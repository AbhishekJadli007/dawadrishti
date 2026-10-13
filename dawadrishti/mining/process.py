"""Process mining on the ERP event log (implemented from scratch; pm4py is AGPL, this project is MIT).

  discovery     directly-follows graph (DFG) with frequencies and mean waiting times, start/end activities
  variants      the distinct activity sequences and how many cases follow each
  conformance   six rules taken from published quality-clearance processes (JMHIDPCL, Tamil Nadu, Jan Aushadhi)
  performance   waiting time between key steps, lab turnaround per lab and buyer, bottlenecks
  benchmarking  every buyer's conformance and speed side by side (the national league table)
  root cause    what drives rule-breaking: a decision tree + rates by lab turnaround
"""
from __future__ import annotations

import json
import sqlite3

import duckdb
import numpy as np
import pandas as pd
from sklearn.tree import DecisionTreeClassifier

from .. import config as C
from ..erp.simulate import DEBAR_MONTHS

LAB_TAT_LIMIT_DAYS = 21   # [GUESS] contractual lab turnaround limit, documented in ASSUMPTIONS.md
RECALL_LIMIT_DAYS = 2

RULES = {
    "R1": ("Issued before quality clearance", "Untested medicine must not reach patients"),
    "R2": ("Failed batch already issued, not recalled within 2 days", "Failed medicine must come back"),
    "R3": ("Sample sent to lab without blind coding", "Blind testing prevents tampering"),
    "R4": ("Payment released before clearance", "No payment for stock that may fail"),
    "R5": ("Order placed with a supplier already debarred by another buyer", "A supplier debarred in one state should not win orders in another"),
    "R6": (f"Lab turnaround over {LAB_TAT_LIMIT_DAYS} days", "Slow tests create pressure to release untested stock"),
}


def load_log(buyer: str | None = None) -> pd.DataFrame:
    con = duckdb.connect(str(C.WAREHOUSE_DB), read_only=True)
    q = "select case_id, buyer_id, buyer, activity, ts, resource, supplier_key, supplier, generic_name, dosage_form from v_events"
    log = con.execute(q + (" where buyer_id = ?" if buyer else ""), [buyer] if buyer else []).df()
    con.close()
    log["ts"] = pd.to_datetime(log.ts, format="ISO8601")
    return log.sort_values(["case_id", "ts"]).reset_index(drop=True)


def discover(log: pd.DataFrame) -> dict:
    log = log.sort_values(["case_id", "ts"])
    nxt = log.groupby("case_id").shift(-1)
    pairs = pd.DataFrame({"source": log.activity, "target": nxt.activity,
                          "wait_h": (nxt.ts - log.ts).dt.total_seconds() / 3600}).dropna()
    dfg = pairs.groupby(["source", "target"]).agg(count=("wait_h", "size"), mean_wait_days=("wait_h", lambda x: x.mean() / 24)).reset_index()
    firsts = log.groupby("case_id").activity.first().value_counts()
    lasts = log.groupby("case_id").activity.last().value_counts()
    return {
        "activities": log.activity.value_counts().to_dict(),
        "edges": dfg.round(2).to_dict(orient="records"),
        "start": firsts.to_dict(), "end": lasts.to_dict(), "cases": int(log.case_id.nunique()), "events": len(log),
    }


def variants(log: pd.DataFrame, top: int = 10) -> list[dict]:
    seq = log.sort_values(["case_id", "ts"]).groupby("case_id").activity.agg(lambda s: " → ".join(s))
    vc = seq.value_counts()
    total = vc.sum()
    return [{"variant": v, "cases": int(n), "share": round(n / total, 4), "steps": v.count("→") + 1} for v, n in vc.head(top).items()]


def _first(log, activity):
    return log[log.activity == activity].groupby("case_id").ts.min()


def case_table(log: pd.DataFrame) -> pd.DataFrame:
    """One row per case with the timestamps that the rules and performance measures need."""
    acts = ["PO created", "Goods received", "Sample drawn", "Sample coded", "Sent to lab", "Report received", "Cleared",
            "Held", "Issued", "Recall started", "Payment released"]
    t = pd.DataFrame({a: _first(log, a) for a in acts})
    meta = log.groupby("case_id").agg(buyer_id=("buyer_id", "first"), buyer=("buyer", "first"), supplier_key=("supplier_key", "first"),
                                      supplier=("supplier", "first"), generic_name=("generic_name", "first"),
                                      dosage_form=("dosage_form", "first"))
    labs = log[log.activity == "Sent to lab"].groupby("case_id").resource.first().rename("lab")
    return meta.join(t).join(labs)


def conformance(log: pd.DataFrame) -> pd.DataFrame:
    ct = case_table(log)
    v = []

    def add(mask, rule, detail):
        for cid, row in ct[mask].iterrows():
            v.append({"case_id": cid, "buyer_id": row.buyer_id, "buyer": row.buyer, "rule": rule, "rule_name": RULES[rule][0],
                      "supplier": row.supplier, "product": row.generic_name, "detail": detail(row)})

    issued = ct["Issued"].notna()
    add(issued & (ct["Cleared"].isna() | (ct["Issued"] < ct["Cleared"])), "R1",
        lambda r: f"issued {r['Issued']:%d %b %Y}; " + (f"cleared {r['Cleared']:%d %b %Y}" if pd.notna(r["Cleared"]) else "never cleared (failed)"))
    held_issued = ct["Held"].notna() & issued & (ct["Issued"] < ct["Held"])
    late = ct["Recall started"].isna() | ((ct["Recall started"] - ct["Held"]).dt.total_seconds() / 86400 > RECALL_LIMIT_DAYS)
    add(held_issued & late, "R2", lambda r: "no recall" if pd.isna(r["Recall started"])
        else f"recall started {(r['Recall started'] - r['Held']).days} days after failure")
    add(ct["Sent to lab"].notna() & ct["Sample coded"].isna(), "R3", lambda r: f"sent to {r['lab']} uncoded")
    paid = ct["Payment released"].notna()
    add(paid & (ct["Cleared"].isna() | (ct["Payment released"] < ct["Cleared"])), "R4",
        lambda r: f"paid {r['Payment released']:%d %b %Y}; " + ("never cleared (failed)" if pd.isna(r["Cleared"]) else f"cleared {r['Cleared']:%d %b %Y}"))
    tat = (ct["Report received"] - ct["Sent to lab"]).dt.total_seconds() / 86400
    add(tat > LAB_TAT_LIMIT_DAYS, "R6", lambda r: f"{(r['Report received'] - r['Sent to lab']).days} days at {r['lab']}")

    # R5 reads the debarment history from the event log: an order placed while another buyer's debarment was in force
    erp = sqlite3.connect(C.ERP_DB)
    deb = pd.read_sql("""select e.buyer_id as debarred_by, e.ts as debarred_on, coalesce(s.manufacturer_id, s.supplier_id) as supplier_key
                         from event_log e join supplier s using(supplier_id) where e.activity = 'Supplier debarred'""", erp)
    erp.close()
    deb["debarred_on"] = pd.to_datetime(deb.debarred_on, format="ISO8601")
    d = ct.reset_index().merge(deb, on="supplier_key", how="inner")
    d = d[(d.debarred_by != d.buyer_id) & (d["PO created"] > d.debarred_on)
          & (d["PO created"] < d.debarred_on + pd.DateOffset(months=DEBAR_MONTHS))]
    d = d.sort_values("debarred_on").drop_duplicates("case_id", keep="last")
    for r in d.itertuples():
        v.append({"case_id": r.case_id, "buyer_id": r.buyer_id, "buyer": r.buyer, "rule": "R5", "rule_name": RULES["R5"][0],
                  "supplier": r.supplier, "product": r.generic_name, "detail": f"debarred by {r.debarred_by} on {r.debarred_on:%d %b %Y}"})
    return pd.DataFrame(v)


def performance(log: pd.DataFrame) -> dict:
    ct = case_table(log)
    days = lambda a, b: (ct[b] - ct[a]).dt.total_seconds() / 86400
    steps = {
        "Order to receipt": days("PO created", "Goods received"),
        "Receipt to sample": days("Goods received", "Sample drawn"),
        "Lab turnaround": days("Sent to lab", "Report received"),
        "Report to decision": days("Report received", "Cleared").fillna(days("Report received", "Held")),
        "Clearance to issue": days("Cleared", "Issued").where(lambda x: x >= 0),
        "Time in quarantine": days("Goods received", "Cleared"),
    }
    summary = [{"step": k, "median_days": round(float(v.median()), 1), "p90_days": round(float(v.quantile(0.9)), 1),
                "cases": int(v.notna().sum())} for k, v in steps.items()]
    bottleneck = max(summary, key=lambda x: x["median_days"])["step"]
    tat = days("Sent to lab", "Report received")
    by_lab = tat.groupby(ct.lab).agg(["median", "mean", "count"]).round(1).reset_index().rename(columns={"lab": "lab"})
    return {"steps": summary, "bottleneck": bottleneck, "lab_turnaround": by_lab.to_dict(orient="records")}


def benchmark(log: pd.DataFrame, viol: pd.DataFrame) -> list[dict]:
    ct = case_table(log)
    out = []
    for (bid, name), g in ct.groupby(["buyer_id", "buyer"]):
        vb = viol[viol.buyer_id == bid] if len(viol) else viol
        row = {"buyer_id": bid, "buyer": name, "cases": len(g),
               "conformance": round(1 - vb.case_id.nunique() / len(g), 4),
               "median_lab_tat_days": round(float(((g["Report received"] - g["Sent to lab"]).dt.total_seconds() / 86400).median()), 1),
               "median_quarantine_days": round(float(((g["Cleared"] - g["Goods received"]).dt.total_seconds() / 86400).median()), 1)}
        for r in RULES:
            row[r] = int((vb.rule == r).sum()) if len(vb) else 0
        out.append(row)
    return sorted(out, key=lambda x: -x["conformance"])


def root_cause(log: pd.DataFrame, viol: pd.DataFrame) -> dict:
    """Why do batches get issued before clearance? Rates by lab-turnaround band + a small decision tree."""
    ct = case_table(log)
    ct["tat_days"] = (ct["Report received"] - ct["Sent to lab"]).dt.total_seconds() / 86400
    ct["early_issue"] = ct.index.isin(viol[viol.rule == "R1"].case_id) if len(viol) else False
    bands = pd.cut(ct.tat_days, [0, 7, 14, 21, 28, 45, 999], labels=["0-7", "7-14", "14-21", "21-28", "28-45", "45+"])
    by_band = ct.groupby(bands, observed=True).early_issue.agg(["mean", "count"]).reset_index()
    X = pd.get_dummies(ct[["buyer", "lab", "dosage_form"]].fillna("?"), dtype=float)
    X["tat_days"] = ct.tat_days.fillna(ct.tat_days.median())
    tree = DecisionTreeClassifier(max_depth=3, min_samples_leaf=40, random_state=C.SEED).fit(X, ct.early_issue)
    imp = sorted(zip(X.columns, tree.feature_importances_), key=lambda x: -x[1])[:6]
    return {"early_issue_by_lab_tat": [{"band": str(r[0]), "rate": round(float(r[1]), 4), "cases": int(r[2])} for r in by_band.itertuples(index=False)],
            "drivers": [{"feature": f, "importance": round(float(w), 3)} for f, w in imp if w > 0]}


def run_all() -> dict:
    log = load_log()
    viol = conformance(log)
    out = {
        "rules": {k: {"name": a, "why": b} for k, (a, b) in RULES.items()},
        "discovery": discover(log),
        "discovery_by_buyer": {b: discover(g) for b, g in log.groupby("buyer_id")},
        "variants": variants(log),
        "conformance_summary": viol.groupby(["rule", "rule_name"]).case_id.nunique().reset_index(name="cases").to_dict(orient="records"),
        "violations_sample": viol.sort_values("case_id").groupby("rule").head(25).to_dict(orient="records"),
        "performance": performance(log),
        "benchmark": benchmark(log, viol),
        "root_cause": root_cause(log, viol),
    }
    C.ARTIFACTS.mkdir(exist_ok=True)
    viol.to_csv(C.ARTIFACTS / "violations.csv", index=False)
    (C.ARTIFACTS / "process_mining.json").write_text(json.dumps(out, indent=1, default=str))
    return out


def main():
    out = run_all()
    print("cases", out["discovery"]["cases"], "events", out["discovery"]["events"], "variants (top):", out["variants"][0]["share"])
    print("conformance:", out["conformance_summary"])
    print("bottleneck:", out["performance"]["bottleneck"], out["performance"]["steps"])
    for b in out["benchmark"]:
        print(f"  {b['buyer']:28s} conformance {b['conformance']:.1%} lab TAT {b['median_lab_tat_days']}d  " +
              " ".join(f"{r}={b[r]}" for r in RULES))
    print("root cause:", out["root_cause"])


if __name__ == "__main__":
    main()
