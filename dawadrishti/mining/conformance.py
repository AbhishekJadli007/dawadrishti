"""Declarative conformance checking: rules are data, and one engine checks any event log.

Rule kinds (on first occurrences of each activity in a case):
  precedence(a, b)          whenever b happens, a must have happened before it
  response(a, b, days)      whenever a happens, b must follow within `days` (missing b counts unless missing_ok)
  requires(a, b)            whenever b happens, a must also happen (in any order)
Optional: `given=(x, y)` limits a rule to cases where x happened before y; `when={attr: values}` limits it by case attribute.

Two uses:
  1. Cross-check: the ERP's hand-written rules (process.py) re-expressed as data must give the same counts.
  2. External validation: the same engine on the public BPI Challenge 2019 purchase-to-pay log (SAP, 1.5M events).
     python -m dawadrishti.mining.conformance --bpi path/to/BPI_Challenge_2019.xes (or the CSV export)
"""
from __future__ import annotations

import argparse
import gzip
import json
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field

import pandas as pd

from .. import config as C


@dataclass
class Rule:
    id: str
    name: str
    kind: str                      # precedence | response | requires
    a: str
    b: str
    days: float | None = None
    missing_ok: bool = False
    given: tuple[str, str] | None = None
    when: dict = field(default_factory=dict)


def first_times(log: pd.DataFrame) -> pd.DataFrame:
    return log.groupby(["case_id", "activity"]).ts.min().unstack()


def check(log: pd.DataFrame, rules: list[Rule], attrs: pd.DataFrame | None = None) -> pd.DataFrame:
    """Returns one row per (case, violated rule)."""
    t = first_times(log)
    col = lambda a: t[a] if a in t else pd.Series(pd.NaT, index=t.index)
    out = []
    for r in rules:
        scope = pd.Series(True, index=t.index)
        if r.given:
            scope &= col(r.given[0]).notna() & col(r.given[1]).notna() & (col(r.given[0]) < col(r.given[1]))
        for k, vals in r.when.items():
            scope &= attrs.reindex(t.index)[k].isin(vals) if attrs is not None else False
        a, b = col(r.a), col(r.b)
        if r.kind == "precedence":
            bad = b.notna() & (a.isna() | (a > b))
        elif r.kind == "requires":
            bad = b.notna() & a.isna()
        elif r.kind == "response":
            late = (b - a).dt.total_seconds() / 86400 > r.days
            bad = a.notna() & (late.fillna(False) if r.missing_ok else (b.isna() | late))
        else:
            raise ValueError(r.kind)
        out += [{"case_id": c, "rule": r.id} for c in t.index[scope & bad]]
    return pd.DataFrame(out, columns=["case_id", "rule"])


def summary(viol: pd.DataFrame, rules: list[Rule], cases: int, scoped: dict | None = None) -> list[dict]:
    n = viol.rule.value_counts()
    return [{**{k: v for k, v in asdict(r).items() if k in ("id", "name", "kind", "a", "b", "days", "when")},
             "violating_cases": int(n.get(r.id, 0)), "cases_in_scope": int((scoped or {}).get(r.id, cases)),
             "share": round(n.get(r.id, 0) / max(1, (scoped or {}).get(r.id, cases)), 4)} for r in rules]


# ------------------------------------------------------------------ 1. the ERP rules, as data
ERP_RULES = [
    Rule("R1", "Issued before quality clearance", "precedence", "Cleared", "Issued"),
    Rule("R2", "Failed batch already issued, not recalled within 2 days", "response", "Held", "Recall started", days=2,
         given=("Issued", "Held")),
    Rule("R3", "Sample sent to lab without blind coding", "requires", "Sample coded", "Sent to lab"),
    Rule("R4", "Payment released before clearance", "precedence", "Cleared", "Payment released"),
    Rule("R6", "Lab turnaround over 21 days", "response", "Sent to lab", "Report received", days=21, missing_ok=True),
]


def crosscheck() -> dict:
    """The declarative engine against the hand-written rules on the same ERP log: counts must agree."""
    from .process import conformance, load_log
    log = load_log()
    hand = conformance(log).groupby("rule").case_id.nunique()
    decl = check(log, ERP_RULES).groupby("rule").case_id.nunique()
    rows = [{"rule": r.id, "name": r.name, "hand_written": int(hand.get(r.id, 0)), "declarative": int(decl.get(r.id, 0))} for r in ERP_RULES]
    return {"cases": int(log.case_id.nunique()), "rules": rows, "agree": all(x["hand_written"] == x["declarative"] for x in rows),
            "note": "R5 needs the debarment register (a join outside the case), so it stays hand-written."}


# ------------------------------------------------------------------ 2. BPI Challenge 2019 (public SAP purchase-to-pay log)
THREE_WAY = ["3-way match, invoice after GR", "3-way match, invoice before GR"]
TRACE_ATTRS = ["Item Category", "Purchasing Document", "GR-Based Inv. Verif.", "Goods Receipt"]
BPI_RULES = [
    Rule("P1", "Invoice cleared (paid) before goods receipt, 3-way match", "precedence", "Record Goods Receipt", "Clear Invoice",
         when={"Item Category": THREE_WAY}),
    Rule("P2", "Invoice recorded before goods receipt where the contract says invoice after GR", "precedence",
         "Record Goods Receipt", "Record Invoice Receipt", when={"Item Category": ["3-way match, invoice after GR"]}),
    Rule("P3", "Goods received before the purchase order item existed", "precedence", "Create Purchase Order Item",
         "Record Goods Receipt"),
    Rule("P4", "Invoice cleared without an invoice receipt", "requires", "Record Invoice Receipt", "Clear Invoice"),
]
DAWADRISHTI_ANALOGUE = {"P1": "R4 payment before clearance", "P2": "R4 payment before clearance (document order)",
                        "P3": "order discipline (no receipt without an order)", "P4": "R4 (payment without its control document)"}


def load_bpi(path: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Reads the XES (optionally .gz) or the CSV export. Returns (events, case attributes)."""
    if path.endswith(".csv") or path.endswith(".csv.gz"):
        d = pd.read_csv(path, encoding="latin-1", usecols=lambda c: c in {"case concept:name", "event concept:name",
                                                                            "event time:timestamp", "case Item Category"})
        log = pd.DataFrame({"case_id": d["case concept:name"], "activity": d["event concept:name"],
                            "ts": pd.to_datetime(d["event time:timestamp"], format="%d-%m-%Y %H:%M:%S.%f", errors="coerce")})
        attrs = d.groupby("case concept:name")["case Item Category"].first().rename("Item Category").to_frame()
        attrs.index.name = "case_id"
        return log.dropna(subset=["ts"]), attrs
    opener = gzip.open if path.endswith(".gz") else open
    rows, attrs = [], {}
    case, cat = None, None
    with opener(path, "rb") as fh:
        for ev, el in ET.iterparse(fh, events=("start", "end")):
            tag = el.tag.rsplit("}", 1)[-1]
            if ev == "start" and tag == "trace":
                case, cat = None, None
            elif ev == "end" and tag == "event":
                kv = {c.get("key"): c.get("value") for c in el}
                rows.append((case, kv.get("concept:name"), kv.get("time:timestamp")))
                el.clear()
            elif ev == "end" and tag == "trace":
                kv = {c.get("key"): c.get("value") for c in el if c.tag.rsplit("}", 1)[-1] != "event"}
                case, cat = kv.get("concept:name"), {k: kv.get(k) for k in TRACE_ATTRS}
                # events were read before the trace's own attributes closed: fill them in
                k = len(rows) - 1
                while k >= 0 and rows[k][0] is None:
                    rows[k] = (case,) + rows[k][1:]
                    k -= 1
                attrs[case] = cat
                el.clear()
    log = pd.DataFrame(rows, columns=["case_id", "activity", "ts"])
    log["ts"] = pd.to_datetime(log.ts, utc=True, errors="coerce", format="ISO8601")
    a = pd.DataFrame.from_dict(attrs, orient="index")
    a.index.name = "case_id"
    return log.dropna(subset=["ts"]), a


PUBLISHED = {"events": 1595923, "cases": 251734, "purchase_documents": 76349, "activities": 42}   # ICPM 2019 challenge page


def run_bpi(path: str) -> dict:
    log, attrs = load_bpi(path)
    viol = check(log, BPI_RULES, attrs)
    cases = log.case_id.nunique()
    cat = attrs["Item Category"]
    scoped = {r.id: int(cat.isin(r.when["Item Category"]).sum()) if r.when else cases for r in BPI_RULES}
    ours = {"events": int(len(log)), "cases": int(cases), "purchase_documents": int(attrs["Purchasing Document"].nunique()),
            "activities": int(log.activity.nunique())}
    # where a rule is enforced by the system, there should be no violations; where it is only policy, there are
    enforced = attrs.groupby("Item Category")["GR-Based Inv. Verif."].apply(lambda s: float((s == "true").mean())).round(3).to_dict()
    p1 = viol[viol.rule == "P1"].case_id
    from .process import discover
    dfg = discover(log.assign(case_id=log.case_id.astype(str)))
    out = {"source": "BPI Challenge 2019 (4TU.ResearchData, doi:10.4121/uuid:d06aff4b-79f0-45e6-8ec8-e19730c248f1)",
           **ours, "reader_check": {"published": PUBLISHED, "ours": ours, "all_match": ours == PUBLISHED},
           "item_categories": cat.value_counts().to_dict(),
           "gr_based_invoice_verification_share": enforced,
           "p1_by_category": cat.reindex(p1).value_counts().to_dict(),
           "rules": summary(viol, BPI_RULES, cases, scoped), "dawadrishti_analogue": DAWADRISHTI_ANALOGUE,
           "reading": ("Rules the system enforces show zero violations: every 'invoice after GR' item has goods-receipt-based "
                       "invoice verification switched on, and no invoice was recorded before its goods receipt. Rules that are "
                       "only policy show violations: invoices cleared for payment before the goods were received."),
           "top_edges": sorted(dfg["edges"], key=lambda e: -e["count"])[:15]}
    (C.ARTIFACTS / "bpi2019_conformance.json").write_text(json.dumps(out, indent=1, default=str))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--bpi", help="path to BPI_Challenge_2019.xes / .xes.gz / .csv")
    a = ap.parse_args(argv)
    if a.bpi:
        out = run_bpi(a.bpi)
        print(f"BPI 2019: {out['events']} events, {out['cases']} cases; matches the published counts: {out['reader_check']['all_match']}")
        print("  GR-based invoice verification by category:", out["gr_based_invoice_verification_share"])
        print("  P1 violations by category:", out["p1_by_category"])
        for r in out["rules"]:
            print(f"  {r['id']} {r['name']}: {r['violating_cases']} of {r['cases_in_scope']} ({r['share']:.1%})")
        return
    x = crosscheck()
    (C.ARTIFACTS / "conformance_crosscheck.json").write_text(json.dumps(x, indent=1))
    print("declarative engine vs hand-written rules:", "AGREE" if x["agree"] else "DISAGREE")
    for r in x["rules"]:
        print(f"  {r['rule']} {r['name']}: hand {r['hand_written']}  declarative {r['declarative']}")


if __name__ == "__main__":
    main()
