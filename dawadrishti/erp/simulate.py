"""Seeded simulator for the ERP's history: 20 months of procurement and quality control for 5 public buyers.

Real inputs: manufacturers, products, failure types and the timing of each manufacturer's national NSQ alerts
(data/staging/nsq_findings.csv). Generated: purchase orders, batches, QC timings, issues, payments, recalls,
and each buyer's (documented) level of rule-following. Buyer names are fictional.

network=False -> today: each buyer sees only its own test results ("isolated ERPs").
network=True  -> DawaDrishti: every buyer sees national alerts and every other buyer's debarments at PO time.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .. import config as C
from .schema import ACTIVITY_MODULE, reset

START, END = pd.Timestamp("2025-01-01"), pd.Timestamp("2026-08-31")


@dataclass(frozen=True)
class BuyerProfile:
    buyer_id: str
    name: str
    level: str
    region: str
    batches: int
    lab_tat_days: float      # mean lab turnaround
    issue_early: float       # P(issue before clearance) when a facility is short
    skip_coding: float       # P(sample sent to lab without blind coding)
    pay_early: float         # P(payment released before clearance)
    recall_delay: float      # mean days from 'Held' to 'Recall started' when stock was already issued
    debar_after: int         # own failures within 12 months before this buyer debars a supplier


# [GUESS] Documented in data/ASSUMPTIONS.md; the point is that buyers differ, and process mining should find how.
BUYERS = [
    BuyerProfile("B1", "National Medicine Agency", "national", "All India", 1600, 9, 0.01, 0.005, 0.01, 1.0, 2),
    BuyerProfile("B2", "Northern State Corporation", "state", "North", 1100, 21, 0.10, 0.05, 0.08, 6.0, 3),
    BuyerProfile("B3", "Western State Corporation", "state", "West", 1200, 14, 0.05, 0.02, 0.03, 3.0, 2),
    BuyerProfile("B4", "Southern State Corporation", "state", "South", 1300, 10, 0.02, 0.01, 0.01, 1.5, 2),
    BuyerProfile("B5", "Eastern State Corporation", "state", "East", 900, 28, 0.07, 0.03, 0.05, 4.0, 3),
]
LABS = ["NABL Lab Delhi", "NABL Lab Mumbai", "NABL Lab Chennai", "NABL Lab Kolkata", "NABL Lab Hyderabad"]
DEBAR_MONTHS = 12         # [GUESS] debarments are time-bound in state tender rules; Kaysons was banned for one year
BASE_FAIL = 0.025          # [SOURCE-ish] national NSQ rate ~2.7% of tested samples (Lok Sabha, 2024-25)


def load_national():
    f = pd.read_csv(C.STAGING / "nsq_findings.csv", parse_dates=False)
    f = f[f.manufacturer_id != "M_UNKNOWN"].copy()
    f["month"] = pd.to_datetime(f.alert_month + "-01")
    return f


def build_masters(f: pd.DataFrame, rng):
    counts = f.groupby(["manufacturer_id", "manufacturer_canonical", "state"]).size().reset_index(name="n")
    repeat = counts[counts.n >= 3].sample(70, random_state=1)
    occasional = counts[counts.n.between(1, 2)].sample(90, random_state=2)
    real = pd.concat([repeat, occasional])
    sup = pd.DataFrame({"supplier_id": [f"S{i:03d}" for i in range(len(real))], "name": real.manufacturer_canonical.values,
                        "state": real.state.values, "manufacturer_id": real.manufacturer_id.values})
    clean = pd.DataFrame({"supplier_id": [f"S{i:03d}" for i in range(len(real), len(real) + 60)],
                          "name": [f"Supplier {i:03d} (no national record)" for i in range(60)],
                          "state": rng.choice(["Gujarat", "Maharashtra", "Telangana", "Tamil Nadu", "Karnataka"], 60),
                          "manufacturer_id": None})
    sup = pd.concat([sup, clean], ignore_index=True)
    sup["debarred_by"], sup["debarred_on"] = None, None
    prods = f.drop_duplicates("generic_name")
    prods = prods[prods.generic_name.str.len().between(4, 60) & ~prods.dosage_form.isin(["Other"])]
    prods = prods.sample(90, random_state=3)
    items = pd.DataFrame({"item_id": [f"I{i:03d}" for i in range(len(prods))], "generic_name": prods.generic_name.values,
                          "dosage_form": prods.dosage_form.values, "therapeutic_class": prods.therapeutic_class.values,
                          "unit_price": np.round(rng.uniform(0.5, 60, len(prods)), 2)})
    return sup, items


def simulate(network: bool = False, seed: int = C.SEED, write: bool = True) -> dict:
    rng = np.random.default_rng(seed)
    f = load_national()
    sup, items = build_masters(f, rng)
    nat = f.groupby("manufacturer_id")
    form_rate = (f.dosage_form.value_counts(normalize=True) / (1 / f.dosage_form.nunique())).clip(0.5, 2.0).to_dict()
    fail_mix = f.groupby("manufacturer_id").primary_failure.agg(lambda s: s.value_counts(normalize=True).to_dict()).to_dict()
    national_mix = f.primary_failure.value_counts(normalize=True)
    critical = {"DEG/EG contamination", "Sterility", "Endotoxin / pyrogen", "Microbial contamination", "Spurious (fake)", "Identity test failed"}

    def national_hits(mid, t, months=12):
        if not isinstance(mid, str) or mid not in nat.groups:
            return 0
        m = nat.get_group(mid).month
        return int(((m < t) & (m >= t - pd.DateOffset(months=months))).sum())

    # rate contracts: each buyer x item has 3 eligible suppliers, ordered by price (L1 first)
    rc = {(b.buyer_id, it): list(rng.choice(sup.supplier_id, 3, replace=False)) for b in BUYERS for it in items.item_id}
    sup_idx = sup.set_index("supplier_id")
    debarred: dict[str, tuple[str, pd.Timestamp]] = {}      # supplier -> (by buyer, date)
    own_fail: dict[tuple[str, str], list] = {}               # (buyer, supplier) -> failure dates
    events, pos, batches, samples, issues, recalls, payments = [], [], [], [], [], [], []
    stats = {"orders_after_failure_elsewhere": 0, "orders_flagged_by_network": 0, "orders_to_debarred": 0}

    def active(deb, t) -> bool:
        return bool(deb) and deb[1] < t < deb[1] + pd.DateOffset(months=DEBAR_MONTHS)

    def ev(b, case, act, t, res, s, it):
        events.append((b, case, act, t, res, s, it, ACTIVITY_MODULE[act]))

    orders = []
    for b in BUYERS:
        n = b.batches
        days = rng.uniform(0, (END - START).days - 60, n)
        for d in np.sort(days):
            orders.append((START + pd.Timedelta(days=float(d)), b))
    orders.sort(key=lambda x: x[0])

    for k, (t, b) in enumerate(orders):
        item = items.item_id.iloc[rng.integers(len(items))]
        cands = rc[(b.buyer_id, item)]
        chosen, warning = None, ""
        for s in cands:
            deb = debarred.get(s)
            own_deb = active(deb, t) and deb[0] == b.buyer_id
            other_deb = active(deb, t) and deb[0] != b.buyer_id
            hits = national_hits(sup_idx.loc[s, "manufacturer_id"], t)
            if own_deb:
                continue
            if network and (other_deb or hits >= 2):
                stats["orders_flagged_by_network"] += 1
                warning = f"skipped {s}: " + ("debarred by another buyer" if other_deb else f"{hits} national alerts in 12 months")
                continue
            chosen = s
            break
        if chosen is None:
            chosen = cands[0]
            warning = (warning + "; " if warning else "") + "no clean alternative on rate contract"
        if active(debarred.get(chosen), t):
            stats["orders_to_debarred"] += 1
        if any(bb != b.buyer_id and any(x < t for x in ds) for (bb, ss), ds in own_fail.items() if ss == chosen):
            stats["orders_after_failure_elsewhere"] += 1

        po = f"PO{k:05d}"
        bid = f"{b.buyer_id}-BT{k:05d}"   # one case = one procurement line, from PO to payment
        qty = int(rng.integers(500, 20000))
        pos.append((po, b.buyer_id, chosen, item, qty, t.isoformat(), warning, "closed"))
        ev(b.buyer_id, bid, "PO created", t, "procurement officer", chosen, item)
        t_app = t + pd.Timedelta(hours=float(rng.uniform(4, 60)))
        ev(b.buyer_id, bid, "PO approved", t_app, "procurement head", chosen, item)
        recv = t_app + pd.Timedelta(days=float(rng.uniform(10, 30)))
        mid = sup_idx.loc[chosen, "manufacturer_id"]
        hits = national_hits(mid, recv)
        factor = (1 + 1.2 * min(hits, 5)) if isinstance(mid, str) else 0.5
        form = items.set_index("item_id").loc[item, "dosage_form"]
        p_fail = min(0.6, BASE_FAIL * factor * form_rate.get(form, 1.0))
        fails = rng.random() < p_fail
        mix = fail_mix.get(mid, national_mix.to_dict()) if fails else {}
        ftype = rng.choice(list(mix.keys()), p=np.array(list(mix.values())) / sum(mix.values())) if fails else ""
        mfg = recv - pd.Timedelta(days=float(rng.uniform(15, 120)))
        batches.append([bid, po, b.buyer_id, chosen, item, f"BN{rng.integers(10**5, 10**6)}", qty, mfg.date().isoformat(),
                        (mfg + pd.DateOffset(months=int(rng.choice([18, 24, 36])))).date().isoformat(), recv.isoformat(),
                        f"{b.region} warehouse {int(rng.integers(1, 4))}", "", None, ftype or "ok"])
        for act, dt in [("Goods received", recv), ("Quarantined", recv + pd.Timedelta(minutes=5))]:
            ev(b.buyer_id, bid, act, dt, "warehouse", chosen, item)

        drawn = recv + pd.Timedelta(days=float(rng.uniform(0.2, 3)))
        ev(b.buyer_id, bid, "Sample drawn", drawn, "QC cell", chosen, item)
        coded = rng.random() >= b.skip_coding
        sent = drawn + pd.Timedelta(days=float(rng.uniform(0.2, 2)))
        if coded:
            ev(b.buyer_id, bid, "Sample coded", drawn + pd.Timedelta(hours=float(rng.uniform(1, 12))), "QC cell", chosen, item)
        lab = LABS[int(rng.integers(len(LABS)))]
        ev(b.buyer_id, bid, "Sent to lab", sent, lab, chosen, item)
        tat = float(rng.gamma(4, b.lab_tat_days / 4)) * (1.3 if lab == "NABL Lab Kolkata" else 1.0)
        reported = sent + pd.Timedelta(days=tat)
        ev(b.buyer_id, bid, "Report received", reported, lab, chosen, item)
        decided = reported + pd.Timedelta(days=float(rng.uniform(0.5, 3)))
        samples.append((f"SM{k:05d}", bid, lab, f"C{rng.integers(10**6, 10**7)}" if coded else "", drawn.isoformat(),
                        sent.isoformat(), reported.isoformat(), "fail" if fails else "pass", decided.isoformat()))

        # pressure to release grows with lab turnaround: P(issue early) = base x (1 + tat/15)
        early = rng.random() < min(0.6, b.issue_early * (1 + tat / 15))
        if early:
            ti = recv + pd.Timedelta(days=float(rng.uniform(1, max(1.5, tat * 0.8))))
            ev(b.buyer_id, bid, "Issued", ti, "warehouse", chosen, item)
            issues.append((f"IS{k:05d}a", bid, f"District hospital {int(rng.integers(1, 40))}", qty // 2, ti.isoformat()))
        pay_early = rng.random() < b.pay_early
        if pay_early:
            tp = recv + pd.Timedelta(days=float(rng.uniform(3, max(3.5, tat))))
            ev(b.buyer_id, bid, "Payment released", tp, "finance", chosen, item)
            payments.append((f"PY{k:05d}", bid, qty * 10.0, tp.isoformat()))

        if not fails:
            ev(b.buyer_id, bid, "Cleared", decided, "technical advisor", chosen, item)
            batches[-1][11] = "cleared"
            if not early:
                ti = decided + pd.Timedelta(days=float(rng.uniform(1, 10)))
                ev(b.buyer_id, bid, "Issued", ti, "warehouse", chosen, item)
                issues.append((f"IS{k:05d}", bid, f"District hospital {int(rng.integers(1, 40))}", qty, ti.isoformat()))
            if not pay_early:
                tp = decided + pd.Timedelta(days=float(rng.uniform(15, 45)))
                ev(b.buyer_id, bid, "Payment released", tp, "finance", chosen, item)
                payments.append((f"PY{k:05d}", bid, qty * 10.0, tp.isoformat()))
        else:
            ev(b.buyer_id, bid, "Held", decided, "technical advisor", chosen, item)
            batches[-1][11] = "held"
            ev(b.buyer_id, bid, "Supplier notified", decided + pd.Timedelta(days=float(rng.uniform(0.5, 2))), "vendor cell", chosen, item)
            if early:
                rs = decided + pd.Timedelta(days=float(rng.exponential(b.recall_delay)))
                ev(b.buyer_id, bid, "Recall started", rs, "warehouse", chosen, item)
                rcl = rs + pd.Timedelta(days=float(rng.uniform(5, 20)))
                ev(b.buyer_id, bid, "Recall closed", rcl, "warehouse", chosen, item)
                recalls.append((f"RC{k:05d}", bid, rs.isoformat(), rcl.isoformat()))
            own_fail.setdefault((b.buyer_id, chosen), []).append(decided)
            recent = [x for x in own_fail[(b.buyer_id, chosen)] if x > decided - pd.DateOffset(months=12)]
            if (len(recent) >= b.debar_after or ftype in critical) and not active(debarred.get(chosen), decided):
                debarred[chosen] = (b.buyer_id, decided)
                ev(b.buyer_id, bid, "Supplier debarred", decided + pd.Timedelta(days=float(rng.uniform(2, 15))), "vendor cell", chosen, item)

    for s, (bb, dt) in debarred.items():           # only debarments still in force at the end of the simulation
        if active((bb, dt), END):
            sup.loc[sup.supplier_id == s, ["debarred_by", "debarred_on"]] = [bb, dt.date().isoformat()]
    stats.update({"batches": len(batches), "failed_batches": sum(1 for x in batches if x[13] != "ok"),
                  "events": len(events), "debarred_suppliers": len(debarred), "debarred_at_end": int(sup.debarred_by.notna().sum()), "network": network})

    if write:
        con = reset()
        pd.DataFrame([b.__dict__ for b in BUYERS])[["buyer_id", "name", "level", "region", "lab_tat_days"]].to_sql("buyer", con, if_exists="append", index=False)
        sup.to_sql("supplier", con, if_exists="append", index=False)
        items.to_sql("item", con, if_exists="append", index=False)
        cols = {"purchase_order": ["po_id", "buyer_id", "supplier_id", "item_id", "qty", "po_date", "risk_warning", "status"],
                "batch": ["batch_id", "po_id", "buyer_id", "supplier_id", "item_id", "batch_no", "qty", "mfg_date", "exp_date",
                          "received_at", "warehouse", "qc_status", "risk_score", "sim_true_quality"],
                "qc_sample": ["sample_id", "batch_id", "lab", "sample_code", "drawn_at", "sent_at", "reported_at", "result", "decided_at"],
                "issue": ["issue_id", "batch_id", "facility", "qty", "issued_at"], "recall": ["recall_id", "batch_id", "started_at", "closed_at"],
                "payment": ["payment_id", "batch_id", "amount", "paid_at"]}
        for table, data in [("purchase_order", pos), ("batch", batches), ("qc_sample", samples), ("issue", issues),
                            ("recall", recalls), ("payment", payments)]:
            pd.DataFrame(data, columns=cols[table]).to_sql(table, con, if_exists="append", index=False)
        e = pd.DataFrame(events, columns=["buyer_id", "case_id", "activity", "ts", "resource", "supplier_id", "item_id", "erp_module"])
        e["ts"] = pd.to_datetime(e.ts).dt.strftime("%Y-%m-%dT%H:%M:%S")
        e.sort_values(["ts"]).to_sql("event_log", con, if_exists="append", index=False)
        con.commit()
        con.close()
    return stats


def main():
    iso = simulate(network=False, write=True)
    net = simulate(network=True, write=False)
    import json
    C.ARTIFACTS.mkdir(exist_ok=True)
    (C.ARTIFACTS / "network_effect.json").write_text(json.dumps({"isolated": iso, "network": net}, indent=2, default=str))
    print("isolated (today):", iso)
    print("with national memory:", net)


if __name__ == "__main__":
    main()
