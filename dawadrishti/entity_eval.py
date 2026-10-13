"""Entity-resolution evaluation: how often does the matcher join two names correctly?

Labelled data: data/er/labelled_pairs.csv, hard candidate pairs drawn from the matcher's own blocking.
  dev   120 pairs, used to find normalisation errors and choose the threshold
  test   80 pairs, drawn after the fixes, labelled with scores hidden, used once for the reported numbers
Labels are "same firm?" from names and addresses only, made by the assistant and flagged for human review.

Two levels: firm (any state) and unit (same firm AND same recorded state; what the memory keys on).
Pairs oversample the hard score band, so these are precision/recall on difficult pairs, not on all pairs.
Run: python -m dawadrishti.entity_eval  ->  artifacts/entity_resolution.json
"""
from __future__ import annotations

import json
import re

import pandas as pd
from rapidfuzz import fuzz

from . import config as C
from .etl import clean, entities

GENERIC = re.compile(r"\b(pharma|lab|healthcare|biotech|lifescience|bioscience|formulation|ind|drugs?|remedy|health|care|"
                     r"medicare|pharmacia|chem|organics|parenterals?|injectables|sciences?|global|international|"
                     r"mfg|co|series|services)\b")


def core(key: str) -> str:
    """The distinctive part of a name: the key without generic industry words."""
    return re.sub(r"\s+", " ", GENERIC.sub(" ", key)).strip()


def _exact(a, b):
    return 100.0 if re.sub(r"\s+", " ", a.lower()).strip() == re.sub(r"\s+", " ", b.lower()).strip() else 0.0


def _v1(a, b):
    return float(fuzz.token_sort_ratio(clean.name_key_v1(a), clean.name_key_v1(b)))


def _v1_eq(a, b):
    return 100.0 if clean.name_key_v1(a) == clean.name_key_v1(b) else 0.0


def _v2(a, b):
    return entities.score(clean.name_key(a), clean.name_key(b))


def _v2_eq(a, b):
    return 100.0 if clean.compact(clean.name_key(a)) == clean.compact(clean.name_key(b)) else 0.0


def _v2_core(a, b):
    """v2 score, capped by how similar the distinctive words are (so "Medizest Pharma" != "Medibest Pharma")."""
    ka, kb = clean.name_key(a), clean.name_key(b)
    s = entities.score(ka, kb)
    ca, cb = core(ka), core(kb)
    if s < 100 and ca and cb:
        s = min(s, float(fuzz.ratio(clean.compact(ca), clean.compact(cb))) + 8)
    return s


MATCHERS = {  # name -> (scorer, threshold)
    "Exact name": (_exact, 100),
    "Normalised name, v1 rules": (_v1_eq, 100),
    "Fuzzy ≥92, v1 rules (before fixes)": (_v1, 92),
    "Normalised name, v2 rules": (_v2_eq, 100),
    "Fuzzy ≥92, v2 rules": (_v2, 92),
    "Fuzzy ≥92, v2 rules + distinctive-word check": (_v2_core, 92),
}


def metrics(truth: pd.Series, pred: pd.Series) -> dict:
    tp, fp = int((truth & pred).sum()), int((~truth & pred).sum())
    fn = int((truth & ~pred).sum())
    p = tp / (tp + fp) if tp + fp else 1.0
    r = tp / (tp + fn) if tp + fn else 1.0
    return {"precision": round(p, 3), "recall": round(r, 3), "f1": round(2 * p * r / (p + r), 3) if p + r else 0.0,
            "tp": tp, "fp": fp, "fn": fn, "n": int(len(truth))}


def evaluate(pairs: pd.DataFrame, scorer, threshold: float) -> dict:
    s = pd.Series([scorer(a, b) for a, b in zip(pairs.name_a, pairs.name_b)], index=pairs.index)
    match = s >= threshold
    same_state = pairs.state_a.eq(pairs.state_b)
    firm_truth = pairs.same_firm.eq(1)
    return {"firm": metrics(firm_truth, match), "unit": metrics(firm_truth & same_state, match & same_state)}


def errors(pairs: pd.DataFrame, scorer, threshold: float) -> list[dict]:
    out = []
    for r in pairs.itertuples():
        s = scorer(r.name_a, r.name_b)
        if (s >= threshold) != bool(r.same_firm):
            out.append({"set": r.set, "a": r.name_a, "b": r.name_b, "score": round(s, 1), "label": int(r.same_firm),
                        "error": "false merge" if s >= threshold else "missed merge", "note": r.note})
    return out


REVIEW_FLOOR = 80   # pairs scoring 80-92 are not merged automatically; they go to a person


def review_queue() -> list[dict]:
    """Every pair in the review band (not merged) and every automatic merge below 100, with the raw spellings behind it."""
    d = pd.read_csv(C.STAGING / "nsq_findings.csv").fillna("")
    d = d[d.manufacturer_id != "M_UNKNOWN"]
    d["key"] = d.manufacturer_name.map(clean.name_key)
    g = d.groupby("key").agg(spellings=("manufacturer_name", lambda s: sorted(s.unique().tolist())[:4]),
                             alerts=("finding_id", "size"), states=("state", lambda s: sorted(set(s))),
                             unit=("manufacturer_id", "first"), firm=("firm_id", "first"))
    must, cannot = entities.load_decisions()
    keys = g.index.tolist()
    blocks: dict = {}
    for i, k in enumerate(keys):
        blocks.setdefault(clean.compact(k)[:4], []).append(i)
    out = []
    for idx in blocks.values():
        for x in range(len(idx)):
            for y in range(x + 1, len(idx)):
                a, b = g.iloc[idx[x]], g.iloc[idx[y]]
                s = entities.score(a.name, b.name)
                if s < REVIEW_FLOOR or s >= 100:
                    continue
                merged = a.firm == b.firm
                pair = frozenset((a.name, b.name))
                decided = "same" if pair in must else "different" if pair in cannot else None
                if not merged and s >= entities.FIRM_THRESHOLD and not decided:
                    continue
                status = (f"reviewer: {decided}" if decided else "merged automatically" if merged else "not merged: needs a decision")
                out.append({"score": round(s, 1), "status": status,
                            "a": a.spellings, "b": b.spellings, "a_alerts": int(a.alerts), "b_alerts": int(b.alerts),
                            "a_states": a.states, "b_states": b.states, "a_firm": a.firm, "b_firm": b.firm})
    # the decisions that move the most alerts first
    return sorted(out, key=lambda r: -(min(r["a_alerts"], r["b_alerts"])))


def population() -> dict:
    d = pd.read_csv(C.STAGING / "nsq_findings.csv").fillna("")
    k = d[d.manufacturer_id != "M_UNKNOWN"]
    per_unit = k.groupby("manufacturer_id").manufacturer_name.nunique()
    return {"rows": int(len(k)), "distinct_raw_strings": int(k.manufacturer.nunique()),
            "distinct_names": int(k.manufacturer_name.nunique()), "units": int(k.manufacturer_id.nunique()),
            "firms": int(k.firm_id.nunique()), "units_with_several_spellings": int((per_unit > 1).sum()),
            "multi_state_firms": int((k.groupby("firm_id").state.nunique() > 1).sum()),
            "max_spellings_in_one_unit": int(per_unit.max())}


LABELS = C.DATA / "er" / "labelled_pairs.csv"


def load_labels() -> tuple[pd.DataFrame, dict]:
    """Labelled pairs, with a person's label (human_label) replacing the assistant's wherever one exists."""
    pairs = pd.read_csv(LABELS).fillna({"note": ""})
    if "human_label" not in pairs:
        pairs["human_label"] = pd.NA
    h = pairs.human_label.notna()
    info = {"reviewed_by_a_person": int(h.sum()), "of": int(len(pairs))}
    if h.any():
        info["assistant_agreement_with_person"] = round(float((pairs.same_firm[h] == pairs.human_label[h].astype(int)).mean()), 3)
        pairs.loc[h, "same_firm"] = pairs.human_label[h].astype(int)
    return pairs, info


def review_labels(which: str = "all"):
    """Terminal tool: label each pair yourself without seeing the assistant's label. Saves after every answer."""
    pairs = pd.read_csv(LABELS)
    for c in ("human_label", "reviewer"):
        if c not in pairs:
            pairs[c] = pd.NA
    pairs["human_label"] = pairs.human_label.astype("object")
    pairs["reviewer"] = pairs.reviewer.astype("object")
    who = input("Your name (saved with each label): ").strip() or "reviewer"
    todo = [i for i in pairs.index if pd.isna(pairs.at[i, "human_label"]) and (which == "all" or pairs.at[i, "set"] == which)]
    print(f"{len(todo)} pairs to review. Answer y (same firm), n (different), s (skip), q (quit). Your answers are saved as you go.")
    for k, i in enumerate(todo, 1):
        r = pairs.loc[i]
        print(f"\n[{k}/{len(todo)}] pair {r.pair_id}")
        print(f"  A: {r.name_a}  ({r.state_a})\n     {r.addr_a}")
        print(f"  B: {r.name_b}  ({r.state_b})\n     {r.addr_b}")
        ans = ""
        while ans not in ("y", "n", "s", "q"):
            ans = input("  Same firm? [y/n/s/q] ").strip().lower()[:1]
        if ans == "q":
            break
        if ans == "s":
            continue
        pairs.at[i, "human_label"] = 1 if ans == "y" else 0
        pairs.at[i, "reviewer"] = who
        pairs.to_csv(LABELS, index=False)
    done = pairs.human_label.notna().sum()
    print(f"\n{done} of {len(pairs)} pairs now have a person's label. Run: python -m dawadrishti.entity_eval")


def run() -> dict:
    pairs, human = load_labels()
    sets = {"dev": pairs[pairs.set == "dev"], "test": pairs[pairs.set == "test"]}
    sure = pairs[(pairs.set == "test") & (pairs.confidence == "sure")]
    table = []
    for name, (scorer, t) in MATCHERS.items():
        row = {"matcher": name}
        for sname, sp in sets.items():
            row[sname] = evaluate(sp, scorer, t)
        row["test_sure_only"] = evaluate(sure, scorer, t)
        table.append(row)
    sweep = []
    for t in [80, 84, 86, 88, 90, 92, 94, 96, 98, 100]:
        for label, scorer in [("v2", _v2), ("v2 + distinctive-word check", _v2_core)]:
            sweep.append({"threshold": t, "scorer": label, "dev": evaluate(sets["dev"], scorer, t),
                          "test": evaluate(sets["test"], scorer, t)})
    chosen = "Fuzzy ≥92, v2 rules"
    review = {k: evaluate(v, _v2, REVIEW_FLOOR) for k, v in sets.items()}
    out = {
        "labelled": {"dev": int(len(sets["dev"])), "test": int(len(sets["test"])),
                     "positives": {k: int(v.same_firm.sum()) for k, v in sets.items()},
                     "unsure": int((pairs.confidence == "unsure").sum()), "human_review": human,
                     "labelled_by": ("assistant from names and addresses; every label awaits human review" if not human["reviewed_by_a_person"]
                                     else f"assistant, with {human['reviewed_by_a_person']} of {human['of']} labels reviewed by a person "
                                          f"(agreement {human.get('assistant_agreement_with_person', 0):.0%}); a person's label wins")},
        "population": population(),
        "rules": [{"rule": r, "why": w} for r, w in RULE_NOTES],
        "matchers": table, "sweep": sweep, "chosen": chosen,
        "with_human_review": {"band": [REVIEW_FLOOR, entities.UNIT_THRESHOLD], "recall_if_reviewers_confirm": review},
        "test_errors": errors(sets["test"], *MATCHERS[chosen]),
        "review_queue": review_queue(),
    }
    (C.ARTIFACTS / "entity_resolution.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    return out


RULE_NOTES = [
    ("Drop prefixes such as \"Mfg By:\", \"M/s.\"", "42 rows began with \"Mfg By:\", so they never reached the right block"),
    ("Drop the legal form: Pvt Ltd, Private Ltd, (P) Ltd, Limited, LLP, Inc", "\"Private Ltd\" and \"Pvt..Ltd\" were left in by v1"),
    ("Treat \"(I)\", \"(India)\" and \"India\" as nothing", "\"Salud Care (I)\" and \"Salud Care (India)\""),
    ("Map Pharmaceuticals and its misspellings to \"pharma\"", "\"Pharmaceticals\", \"Pharnaceuticals\", \"Pharmaceutica ls\""),
    ("Map lab, healthcare, life sciences, bio sciences, biotech, formulation, industries to one form",
     "\"Life Sciences\" vs \"Lifesciences\", \"Helathcare\""),
    ("Drop address residue at the end: \"No\", \"K. No\", \"Unit-II\"", "the name/address split sometimes leaves a plot number word"),
    ("Compare with spaces removed", "\"NitinLifesciences\", \"J.M.Laboratories\", \"CyanoPharma\""),
]


def main(argv=None):
    import sys
    args = sys.argv[1:] if argv is None else argv
    if args and args[0] == "--review":
        review_labels(args[1] if len(args) > 1 else "all")
        return
    out = run()
    print("population:", out["population"])
    for row in out["matchers"]:
        f, u = row["test"]["firm"], row["test"]["unit"]
        print(f"  {row['matcher']:48s} test firm P {f['precision']:.2f} R {f['recall']:.2f} F1 {f['f1']:.2f} | "
              f"unit P {u['precision']:.2f} R {u['recall']:.2f} | dev firm F1 {row['dev']['firm']['f1']:.2f}")
    for s in out["sweep"]:
        print(f"  sweep {s['scorer']:28s} t={s['threshold']:3d} dev F1 {s['dev']['firm']['f1']:.2f} "
              f"(P {s['dev']['firm']['precision']:.2f} R {s['dev']['firm']['recall']:.2f})  test F1 {s['test']['firm']['f1']:.2f} "
              f"(P {s['test']['firm']['precision']:.2f} R {s['test']['firm']['recall']:.2f})")
    print("with review:", out["with_human_review"]["recall_if_reviewers_confirm"]["test"])
    print("review queue:", len(out["review_queue"]), "pairs;", sum(r["status"].startswith("not") for r in out["review_queue"]), "undecided")
    print("test errors:", len(out["test_errors"]))


if __name__ == "__main__":
    main()
