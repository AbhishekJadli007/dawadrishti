import pandas as pd

from dawadrishti.mining import process


def toy_log():
    t = pd.Timestamp("2026-01-01")
    rows = []
    for case, acts in {"A": ["PO created", "Goods received", "Sent to lab", "Report received", "Cleared", "Issued"],
                       "B": ["PO created", "Goods received", "Issued", "Sent to lab", "Report received", "Cleared"]}.items():
        for i, a in enumerate(acts):
            rows.append({"case_id": case, "buyer_id": "B1", "buyer": "Test", "activity": a, "ts": t + pd.Timedelta(days=i),
                         "resource": "lab", "supplier_key": "S", "supplier": "S", "generic_name": "X", "dosage_form": "Tablet"})
    return pd.DataFrame(rows)


def test_discovery_counts_directly_follows_pairs():
    d = process.discover(toy_log())
    pairs = {(e["source"], e["target"]): e["count"] for e in d["edges"]}
    assert pairs[("PO created", "Goods received")] == 2
    assert pairs[("Goods received", "Issued")] == 1
    assert d["cases"] == 2


def test_variants():
    v = process.variants(toy_log())
    assert len(v) == 2 and sum(x["cases"] for x in v) == 2


def test_conformance_on_the_real_event_log_is_consistent():
    log = process.load_log()
    viol = process.conformance(log)
    assert set(viol.rule) <= set(process.RULES)
    r1 = viol[viol.rule == "R1"].case_id
    ct = process.case_table(log).loc[r1]
    assert ((ct["Cleared"].isna()) | (ct["Issued"] < ct["Cleared"])).all()
