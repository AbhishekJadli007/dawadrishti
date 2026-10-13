"""ERP business operations. Each one writes the transaction and its event, and applies the national checks.

  national_check  a supplier's record across India: national alerts, critical failures, debarment by any buyer
  create_po       raise a purchase order; warns (with reasons) when the supplier is risky nationally
  receive         goods receipt: the batch is quarantined and scored for risk
  record_result   lab result: clear or hold; a failure notifies the supplier, recalls issued stock, flags nationally
  issue           release to a facility: BLOCKED unless the batch is cleared (rule R1 enforced, not just monitored)
"""
from __future__ import annotations

import datetime as dt
import threading
import uuid

import duckdb
import joblib
import pandas as pd

from .. import config as C
from .schema import ACTIVITY_MODULE, connect

LOCK = threading.Lock()


def now() -> str:
    return dt.datetime.now().replace(microsecond=0).isoformat()


def _event(con, buyer, case, activity, resource, supplier, item, ts=None):
    con.execute("insert into event_log(buyer_id, case_id, activity, ts, resource, supplier_id, item_id, erp_module) values (?,?,?,?,?,?,?,?)",
                (buyer, case, activity, ts or now(), resource, supplier, item, ACTIVITY_MODULE[activity]))


def national_check(supplier_id: str, as_of: str | None = None) -> dict:
    """The memory's graded response for a supplier, as the ERP sees it at purchase-order time.
    level 3 blocks the PO (override is recorded), 2 and 1 warn, 0 is clear. Same rules as the lookup API."""
    from ..memory import graded_response
    con = connect()
    s = con.execute("select * from supplier where supplier_id = ?", (supplier_id,)).fetchone()
    con.close()
    if not s:
        raise ValueError(f"Unknown supplier {supplier_id}")
    out = {"supplier_id": supplier_id, "name": s["name"], "state": s["state"], "manufacturer_id": s["manufacturer_id"],
           "national_alerts_12m": 0, "critical_12m": 0, "national_alerts_total": 0, "last_alert": None,
           "debarred_by": s["debarred_by"], "debarred_on": s["debarred_on"], "recent_failures": []}
    f = pd.DataFrame(columns=["month", "severity"])
    if s["manufacturer_id"]:
        w = duckdb.connect(str(C.WAREHOUSE_DB), read_only=True)
        f = w.execute("""select month, generic_name, dosage_form, primary_failure, severity, reporting_lab, batch_no
                         from v_findings where manufacturer_id = ? order by month desc""", [s["manufacturer_id"]]).df()
        w.close()
        f = f[f.month <= pd.Timestamp(as_of).strftime("%Y-%m")] if as_of else f
        out.update({"national_alerts_total": int(len(f)), "last_alert": f.month.max() if len(f) else None,
                    "recent_failures": f.head(8).to_dict(orient="records")})
    when = pd.Timestamp(as_of or dt.date.today())
    g = graded_response(f, when, bool(s["debarred_by"]))
    out.update({"national_alerts_12m": g["facts"]["alerts_12m"], "critical_12m": g["facts"]["critical_12m"],
                "response_level": g["level"], "response": g["label"], "response_rule": g["rule"]})
    reasons = []
    if out["debarred_by"]:
        reasons.append(f"debarred by buyer {out['debarred_by']} on {out['debarred_on']} (simulated network)")
    if g["facts"]["critical_12m"]:
        reasons.append(f"{g['facts']['critical_12m']} critical national failure(s) in the last 12 months")
    elif g["facts"]["critical_36m"]:
        reasons.append(f"{g['facts']['critical_36m']} critical national failure(s) in the last 36 months")
    if g["facts"]["alerts_12m"]:
        reasons.append(f"{g['facts']['alerts_12m']} national alert(s) in the last 12 months")
    elif g["facts"]["alerts_36m"]:
        reasons.append(f"{g['facts']['alerts_36m']} national alert(s) in the last 36 months")
    out["level"] = "block" if g["level"] == 3 else "warn" if g["level"] >= 1 else "ok"
    out["reasons"] = reasons
    return out


def contract_status(buyer_id: str, item_id: str) -> dict:
    """Supply position for one item at one buyer: who supplies it (concentration) and how long stock lasts (days of cover).
    A graded response that pauses or holds a supplier is only safe if the buyer can see what that does to supply."""
    con = connect()
    po = pd.read_sql("""select p.supplier_id, s.name, p.qty, p.po_date from purchase_order p join supplier s using(supplier_id)
                        where p.buyer_id = ? and p.item_id = ?""", con, params=(buyer_id, item_id))
    b = pd.read_sql("select batch_id, qty, qc_status from batch where buyer_id = ? and item_id = ?", con, params=(buyer_id, item_id))
    iss = pd.read_sql("""select i.qty, i.issued_at from issue i join batch b using(batch_id)
                         where b.buyer_id = ? and b.item_id = ?""", con, params=(buyer_id, item_id))
    con.close()
    out = {"buyer_id": buyer_id, "item_id": item_id, "suppliers": [], "hhi": None, "top_share": None,
           "days_of_cover": None, "days_of_cover_with_testing": None, "daily_use": None}
    if len(po):
        po["po_date"] = pd.to_datetime(po.po_date, format="ISO8601")
        recent = po[po.po_date >= po.po_date.max() - pd.DateOffset(months=12)]
        share = recent.groupby(["supplier_id", "name"]).qty.sum()
        share = (share / share.sum()).sort_values(ascending=False)
        out["suppliers"] = [{"supplier_id": k[0], "name": k[1], "share": round(float(v), 3)} for k, v in share.items()]
        out["hhi"] = round(float((share ** 2).sum()), 3)
        out["top_share"] = round(float(share.iloc[0]), 3)
    if len(iss):
        iss["issued_at"] = pd.to_datetime(iss.issued_at, format="ISO8601")
        last90 = iss[iss.issued_at >= iss.issued_at.max() - pd.Timedelta(days=90)]
        daily = float(last90.qty.sum()) / 90
        usable = max(0, int(b[b.qc_status.eq("cleared")].qty.sum() - iss.qty.sum()))
        testing = int(b[b.qc_status.eq("quarantine")].qty.sum())
        if daily > 0:
            out.update({"daily_use": round(float(daily), 1), "usable_stock": usable, "in_testing": testing,
                        "days_of_cover": round(float(usable / daily), 1), "days_of_cover_with_testing": round(float((usable + testing) / daily), 1)})
    out["concentration"] = ("single source" if out["top_share"] and out["top_share"] > 0.9 else
                            "concentrated" if out["hhi"] and out["hhi"] > 0.5 else "diversified" if out["hhi"] else "no history")
    return out


def create_po(buyer_id: str, item_id: str, supplier_id: str, qty: int, override: bool = False) -> dict:
    check = national_check(supplier_id)
    if check["level"] == "block" and not override:
        return {"created": False, "check": check, "message": "Blocked by national check. Choose another supplier or record an override."}
    po, case = f"PO-L{uuid.uuid4().hex[:6].upper()}", f"{buyer_id}-L{uuid.uuid4().hex[:6].upper()}"
    with LOCK:
        con = connect()
        con.execute("insert into purchase_order values (?,?,?,?,?,?,?,?)",
                    (po, buyer_id, supplier_id, item_id, qty, now(), "; ".join(check["reasons"]), "open"))
        _event(con, buyer_id, case, "PO created", "procurement officer", supplier_id, item_id)
        _event(con, buyer_id, case, "PO approved", "procurement head", supplier_id, item_id)
        con.execute("insert into batch(batch_id, po_id, buyer_id, supplier_id, item_id, qty, qc_status) values (?,?,?,?,?,?,?)",
                    (case, po, buyer_id, supplier_id, item_id, qty, "ordered"))
        con.commit()
        con.close()
    return {"created": True, "po_id": po, "case_id": case, "check": check}


def _batch_risk(supplier_id: str, item_id: str) -> float:
    try:
        bundle = joblib.load(C.ARTIFACTS / "batch_risk.joblib")
    except Exception:  # missing, or saved by another scikit-learn version: score unavailable, ERP still works
        return 0.0
    chk = national_check(supplier_id)
    con = connect()
    it = con.execute("select dosage_form, therapeutic_class from item where item_id = ?", (item_id,)).fetchone()
    con.close()
    row = {c: 0.0 for c in bundle["columns"]}
    row.update({"nat_12m": chk["national_alerts_12m"], "nat_crit_12m": chk["critical_12m"], "nat_total": chk["national_alerts_total"],
                "no_national_record": 0 if chk["manufacturer_id"] else 1})
    for col in (f"dosage_form_{it['dosage_form']}", f"therapeutic_class_{it['therapeutic_class']}"):
        if col in row:
            row[col] = 1.0
    return round(float(bundle["model"].predict_proba(pd.DataFrame([row])[bundle["columns"]])[0, 1]), 4)


def receive(case_id: str, batch_no: str, mfg_date: str, exp_date: str, warehouse: str = "Central warehouse") -> dict:
    with LOCK:
        con = connect()
        b = con.execute("select * from batch where batch_id = ?", (case_id,)).fetchone()
        if not b or b["qc_status"] != "ordered":
            con.close()
            raise ValueError("Batch not found or already received")
        risk = _batch_risk(b["supplier_id"], b["item_id"])
        con.execute("update batch set batch_no=?, mfg_date=?, exp_date=?, received_at=?, warehouse=?, qc_status='quarantine', risk_score=? where batch_id=?",
                    (batch_no, mfg_date, exp_date, now(), warehouse, risk, case_id))
        _event(con, b["buyer_id"], case_id, "Goods received", "warehouse", b["supplier_id"], b["item_id"])
        _event(con, b["buyer_id"], case_id, "Quarantined", "warehouse", b["supplier_id"], b["item_id"])
        _event(con, b["buyer_id"], case_id, "Sample drawn", "QC cell", b["supplier_id"], b["item_id"])
        _event(con, b["buyer_id"], case_id, "Sample coded", "QC cell", b["supplier_id"], b["item_id"])
        _event(con, b["buyer_id"], case_id, "Sent to lab", "NABL lab", b["supplier_id"], b["item_id"])
        con.commit()
        con.close()
    return {"case_id": case_id, "status": "quarantine", "risk_score": risk}


def record_result(case_id: str, passed: bool, failure: str = "") -> dict:
    with LOCK:
        con = connect()
        b = con.execute("select * from batch where batch_id = ?", (case_id,)).fetchone()
        if not b or b["qc_status"] != "quarantine":
            con.close()
            raise ValueError("Batch is not awaiting a lab result")
        _event(con, b["buyer_id"], case_id, "Report received", "NABL lab", b["supplier_id"], b["item_id"])
        actions = []
        if passed:
            con.execute("update batch set qc_status='cleared' where batch_id=?", (case_id,))
            _event(con, b["buyer_id"], case_id, "Cleared", "technical advisor", b["supplier_id"], b["item_id"])
            actions.append("Quality clearance issued; batch can be released.")
        else:
            con.execute("update batch set qc_status='held', sim_true_quality=? where batch_id=?", (failure or "failed", case_id))
            _event(con, b["buyer_id"], case_id, "Held", "technical advisor", b["supplier_id"], b["item_id"])
            _event(con, b["buyer_id"], case_id, "Supplier notified", "vendor cell", b["supplier_id"], b["item_id"])
            actions.append("Batch held and supplier notified.")
            if con.execute("select count(*) from issue where batch_id=?", (case_id,)).fetchone()[0]:
                _event(con, b["buyer_id"], case_id, "Recall started", "warehouse", b["supplier_id"], b["item_id"])
                actions.append("Stock already issued: recall started.")
            con.execute("update supplier set debarred_by=coalesce(debarred_by, ?), debarred_on=coalesce(debarred_on, ?) where supplier_id=?",
                        (b["buyer_id"], dt.date.today().isoformat(), b["supplier_id"]))
            _event(con, b["buyer_id"], case_id, "Supplier debarred", "vendor cell", b["supplier_id"], b["item_id"])
            actions.append("Failure shared nationally: every buyer now sees this supplier as debarred at purchase-order time.")
        con.commit()
        con.close()
    return {"case_id": case_id, "status": "cleared" if passed else "held", "actions": actions}


def issue(case_id: str, facility: str, qty: int) -> dict:
    with LOCK:
        con = connect()
        b = con.execute("select * from batch where batch_id = ?", (case_id,)).fetchone()
        if not b:
            con.close()
            raise ValueError("Unknown batch")
        if b["qc_status"] != "cleared":
            con.close()
            return {"issued": False, "rule": "R1", "message": f"Blocked: batch status is '{b['qc_status']}'. "
                                                              "Only batches with quality clearance can be issued."}
        con.execute("insert into issue values (?,?,?,?,?)", (f"IS-L{uuid.uuid4().hex[:6]}", case_id, facility, qty, now()))
        _event(con, b["buyer_id"], case_id, "Issued", "warehouse", b["supplier_id"], b["item_id"])
        con.commit()
        con.close()
    return {"issued": True, "case_id": case_id}


def queue(buyer_id: str) -> list[dict]:
    con = connect()
    rows = con.execute("""select b.batch_id, b.po_id, b.qc_status, b.risk_score, b.received_at, b.batch_no, s.name supplier, s.supplier_id,
                                 i.generic_name, i.dosage_form, b.qty
                          from batch b join supplier s using(supplier_id) join item i using(item_id)
                          where b.buyer_id = ? and b.qc_status in ('ordered', 'quarantine', 'cleared', 'held')
                            and (b.batch_id like '%-L%')
                          order by case b.qc_status when 'quarantine' then 0 when 'ordered' then 1 else 2 end, b.risk_score desc""",
                       (buyer_id,)).fetchall()
    con.close()
    return [dict(r) for r in rows]


def case_timeline(case_id: str) -> dict:
    con = connect()
    ev = [dict(r) for r in con.execute("select activity, ts, resource, erp_module from event_log where case_id=? order by ts, event_id", (case_id,))]
    b = con.execute("""select b.*, s.name supplier, i.generic_name, i.dosage_form from batch b join supplier s using(supplier_id)
                       join item i using(item_id) where batch_id=?""", (case_id,)).fetchone()
    con.close()
    return {"case_id": case_id, "batch": dict(b) if b else None, "events": ev}


def seed_live(per_buyer: int = 6) -> int:
    """A few open purchase orders/receipts per buyer so the live ERP desk has work in it."""
    con = connect()
    if con.execute("select count(*) from batch where batch_id like '%-L%'").fetchone()[0]:
        con.close()
        return 0
    buyers = [r[0] for r in con.execute("select buyer_id from buyer")]
    pairs = con.execute("""select buyer_id, item_id, supplier_id from purchase_order where supplier_id in
                           (select supplier_id from supplier where debarred_by is null) group by buyer_id, item_id, supplier_id""").fetchall()
    con.close()
    import random
    rnd = random.Random(C.SEED)
    n = 0
    for b in buyers:
        mine = [p for p in pairs if p[0] == b]
        for p in rnd.sample(mine, min(per_buyer, len(mine))):
            r = create_po(b, p[1], p[2], rnd.randint(1000, 20000))
            if r.get("created"):
                receive(r["case_id"], f"BN{rnd.randint(10**5, 10**6)}", "2026-08-01", "2028-07-31")
                n += 1
    return n
