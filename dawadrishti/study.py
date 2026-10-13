"""The headline study: does a national quality memory have anything to remember? (REAL data only)

For every manufacturer in CDSCO's published NSQ alerts, order its failures by month and ask:
after the first recorded failure, how many more followed, how soon, detected where, before it stopped appearing?

  repeat share      share of failed batches that came from a firm ALREADY on the national record (an earlier month)
                    = the share a working memory could have flagged in advance
  lead time         months between a firm's first recorded failure and its next one
  elsewhere         share of repeat failures detected by a different lab / a different state than any earlier one
  concentration     a few units or a long tail? failures per unit, top-10% share, Gini
  ablation          every number recomputed under four matching rules, from exact strings to loose fuzzy matching
  worked cases      the named firms from the problem statement, checked in the data

Confidence intervals: cluster bootstrap over manufacturers (1,000 resamples).
"""
from __future__ import annotations

import json
import re
from collections import defaultdict

import numpy as np
import pandas as pd
from rapidfuzz import fuzz

from . import config as C
from .etl import clean

CENTRAL_LAB = re.compile(r"\b(cdl|cdtl|rdtl|central|ipc|nibs|cdsco)\b", re.I)
RNG = np.random.default_rng(C.SEED)


def load() -> pd.DataFrame:
    d = pd.read_csv(C.STAGING / "nsq_findings.csv").fillna({"reporting_lab": "", "manufacturer_name": ""})
    d = d[(d.manufacturer_id != "M_UNKNOWN") & (d.state != "Unknown")].copy()
    d["t"] = pd.to_datetime(d.alert_month + "-01")
    d["lab_norm"] = d.reporting_lab.str.lower().str.replace(r"[^a-z]", " ", regex=True).str.split().str.join(" ")
    # where was the sample's failure detected? Only state labs identify a state; central and regional labs test for many states.
    def det_state(r):
        if r.reporting_source != "State lab" or CENTRAL_LAB.search(r.reporting_lab):
            return None
        s, how = clean.state_of(r.reporting_lab)
        return s if s not in ("Unknown", "Outside India") else None
    d["detected_state"] = d.apply(det_state, axis=1)
    d["key"] = d.manufacturer_name.map(clean.name_key)
    return d


# ------------------------------------------------------------------ identity under different matching rules
def identities(d: pd.DataFrame) -> dict[str, pd.Series]:
    out = {
        "exact string": d.manufacturer.str.lower().str.replace(r"\s+", " ", regex=True).str.strip(),
        "normalised name, same state": d.key + "|" + d.state,
        "fuzzy ≥92, same state (default)": d.manufacturer_id,
        "fuzzy ≥92, units joined across states (firm)": d.firm_id,
    }
    # loose: fuzzy >= 85 within the same first-4-character block, ACROSS states (firm level rather than unit level)
    keys = d.key.unique()
    parent = {k: k for k in keys}

    def find(k):
        while parent[k] != k:
            parent[k] = parent[parent[k]]
            k = parent[k]
        return k
    blocks = defaultdict(list)
    for k in keys:
        blocks[k[:4]].append(k)
    for ks in blocks.values():
        for i in range(len(ks)):
            for j in range(i + 1, len(ks)):
                if fuzz.token_sort_ratio(ks[i], ks[j]) >= 85:
                    parent[find(ks[j])] = find(ks[i])
    out["loose: fuzzy ≥85, any state (firm level)"] = d.key.map(find)
    return out


# ------------------------------------------------------------------ measures
def measures(d: pd.DataFrame, ident: pd.Series) -> dict:
    d = d.assign(firm=ident.values).sort_values("t")
    first = d.groupby("firm").t.transform("min")
    is_repeat = d.t > first                                   # an EARLIER month already on record
    months = d.groupby("firm").t.apply(lambda s: sorted(set(s)))
    gaps_first = [(m[1] - m[0]).days / 30.44 for m in months if len(m) >= 2]
    gaps_all = [(b - a).days / 30.44 for m in months for a, b in zip(m, m[1:])]
    lead = ((d.t - first).dt.days / 30.44)[is_repeat]

    # detected elsewhere: a repeat failure whose lab (or state) was not among the firm's earlier detections
    new_lab, new_state, state_known = [], [], []
    seen_lab, seen_state = defaultdict(set), defaultdict(set)
    for month, grp in d.groupby("t", sort=True):
        for r in grp.itertuples():
            ds = r.detected_state if isinstance(r.detected_state, str) else None
            if r.t > first[r.Index]:
                new_lab.append(r.lab_norm not in seen_lab[r.firm])
                if ds and seen_state[r.firm]:
                    state_known.append(True)
                    new_state.append(ds not in seen_state[r.firm])
        for r in grp.itertuples():
            seen_lab[r.firm].add(r.lab_norm)
            if isinstance(r.detected_state, str):
                seen_state[r.firm].add(r.detected_state)

    per_firm = d.groupby("firm").size().sort_values(ascending=False)
    top10 = per_firm.head(max(1, int(round(len(per_firm) * 0.10)))).sum() / per_firm.sum()
    x = np.sort(per_firm.values)
    gini = (2 * np.arange(1, len(x) + 1) - len(x) - 1).dot(x) / (len(x) * x.sum())
    buckets = pd.cut(per_firm, [0, 1, 4, 9, 10**6], labels=["1", "2-4", "5-9", "10+"]).value_counts().reindex(["1", "2-4", "5-9", "10+"])
    return {
        "failed_batches": int(len(d)), "firms": int(per_firm.size),
        "repeat_share": float(is_repeat.mean()),
        "repeat_share_critical": float(is_repeat[d.severity.eq("critical")].mean()),
        "firms_with_repeat": int(sum(len(m) >= 2 for m in months)),
        "median_months_first_to_next": float(np.median(gaps_first)) if gaps_first else None,
        "median_months_between_failures": float(np.median(gaps_all)) if gaps_all else None,
        "median_lead_months_for_repeats": float(lead.median()) if len(lead) else None,
        "repeat_detected_by_new_lab": float(np.mean(new_lab)) if new_lab else None,
        "repeat_detected_in_new_state": float(np.mean(new_state)) if new_state else None,
        "repeats_with_state_known": int(len(state_known)),
        "top10pct_firms_share": float(top10), "gini": float(gini),
        "firms_by_failures": {k: int(v) for k, v in buckets.items()},
    }


def bootstrap(d: pd.DataFrame, ident: pd.Series, n: int = 1000) -> dict:
    """Cluster bootstrap over firms for the repeat share and the lead time."""
    d = d.assign(firm=ident.values)
    first = d.groupby("firm").t.transform("min")
    d = d.assign(rep=(d.t > first).astype(float), lead=(d.t - first).dt.days / 30.44)
    g = d.groupby("firm").agg(n=("rep", "size"), reps=("rep", "sum"))
    firms = g.index.values
    shares = []
    for _ in range(n):
        s = g.loc[RNG.choice(firms, len(firms), replace=True)]
        shares.append(s.reps.sum() / s.n.sum())
    return {"repeat_share_ci95": [float(np.percentile(shares, 2.5)), float(np.percentile(shares, 97.5))]}


def worked_cases(d_all: pd.DataFrame) -> list[dict]:
    """The firms named in the problem statement: what did the national record show, and when?"""
    cases = [
        ("Sresan Pharmaceutical (Coldrif)", "sresan", "2025-10", "Coldrif deaths reported from early Oct 2025"),
        ("Maiden Pharmaceuticals (The Gambia)", "maiden", "2022-10", "WHO alert 5 Oct 2022"),
        ("Kaysons Pharma (Rajasthan)", "kayson", "2025-10", "40 samples failed in state testing 2021-23 (Down To Earth)"),
    ]
    txt = d_all.manufacturer.fillna("").str.lower()
    out = []
    for name, pat, incident, note in cases:
        m = d_all[txt.str.contains(pat)]
        before = m[m.alert_month < incident]
        out.append({"case": name, "incident": incident, "note": note, "national_alerts": int(len(m)),
                    "alerts_before_incident": int(len(before)),
                    "first_alert": m.alert_month.min() if len(m) else None,
                    "products": sorted(m.product_name.str.slice(0, 60).unique().tolist())[:6]})
    return out


def run() -> dict:
    d = load()
    d_all = pd.read_csv(C.STAGING / "nsq_findings.csv")
    ids = identities(d)
    by_rule = {name: measures(d, ident) for name, ident in ids.items()}
    default = "fuzzy ≥92, same state (default)"
    out = {
        "data": {"source": "CDSCO NSQ alerts (portal JSON 2019-2026 + PDFs 2017-2018)", "from": d.alert_month.min(),
                 "to": d.alert_month.max(), "records_used": int(len(d)),
                 "excluded": "records with unknown manufacturer, fakes whose named firm denied making them, and unknown state",
                 "outside_india_records": int((d.state == "Outside India").sum())},
        "headline": {**by_rule[default], **bootstrap(d, ids[default])},
        "ablation": by_rule,
        "worked_cases": worked_cases(d_all),
    }
    (C.ARTIFACTS / "memory_study.json").write_text(json.dumps(out, indent=1, default=str))
    return out


def main():
    out = run()
    h = out["headline"]
    print(f"records {out['data']['records_used']} ({out['data']['from']}..{out['data']['to']}), firms {h['firms']}")
    print(f"repeat share {h['repeat_share']:.1%} (95% CI {h['repeat_share_ci95'][0]:.1%}-{h['repeat_share_ci95'][1]:.1%}); "
          f"critical {h['repeat_share_critical']:.1%}")
    print(f"median months first->next {h['median_months_first_to_next']:.1f}; lead for repeats {h['median_lead_months_for_repeats']:.1f}")
    print(f"repeat detected by new lab {h['repeat_detected_by_new_lab']:.1%}; new state {h['repeat_detected_in_new_state']} "
          f"(n={h['repeats_with_state_known']})")
    print(f"top 10% firms share {h['top10pct_firms_share']:.1%}; gini {h['gini']:.2f}; buckets {h['firms_by_failures']}")
    for name, m in out["ablation"].items():
        print(f"  [{name}] firms {m['firms']}, repeat share {m['repeat_share']:.1%}, first->next {m['median_months_first_to_next']}, "
              f"new lab {m['repeat_detected_by_new_lab']:.1%}")
    for c in out["worked_cases"]:
        print("  case:", c)


if __name__ == "__main__":
    main()
