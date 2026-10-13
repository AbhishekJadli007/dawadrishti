"""AI risk models, each evaluated against simple baselines on data it never saw (time split).

1. Future regulatory attention (REAL national data): which units will appear in the next 6 months of NSQ alerts?
   This predicts being sampled AND failing, so it reflects where inspectors look as much as factory quality.
   Used by drug controllers and buyers to choose where to test; never shown on public pages.
   Train: monthly cutoffs up to Sep 2025.  Test: cutoff Mar 2026 -> real alerts Mar-Aug 2026.
   Baselines: most past failures, most recent failure, random.

2. Batch risk (simulated ERP): which incoming batches are most likely to fail the buyer's lab test?
   Used by a buyer's QC cell to test the riskiest batches first.
   Train: batches received in 2025.  Test: 2026.  Baselines: first-in-first-out, random.
"""
from __future__ import annotations

import json
import sqlite3

import duckdb
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

from .. import config as C

FACTORY_FEATURES = ["n_total", "n_12m", "n_6m", "n_3m", "months_since_last", "products", "critical_total", "critical_12m",
                    "alert_months", "span_months", "share_injectable", "share_liquid", "state_hp", "state_uk", "state_gj"]
HORIZON = 6


def _findings():
    con = duckdb.connect(str(C.WAREHOUSE_DB), read_only=True)
    df = con.execute("select manufacturer_id, state, month, severity, dosage_form, generic_name from v_findings where manufacturer_id is not null").df()
    con.close()
    df["t"] = pd.to_datetime(df.month + "-01")
    return df


def factory_features(df: pd.DataFrame, cutoff: pd.Timestamp) -> pd.DataFrame:
    h = df[df.t < cutoff]
    g = h.groupby("manufacturer_id")
    last = g.t.max()
    f = pd.DataFrame({
        "n_total": g.size(),
        "n_12m": h[h.t >= cutoff - pd.DateOffset(months=12)].groupby("manufacturer_id").size(),
        "n_6m": h[h.t >= cutoff - pd.DateOffset(months=6)].groupby("manufacturer_id").size(),
        "n_3m": h[h.t >= cutoff - pd.DateOffset(months=3)].groupby("manufacturer_id").size(),
        "months_since_last": (cutoff - last).dt.days / 30.4,
        "products": g.generic_name.nunique(),
        "critical_total": h[h.severity == "critical"].groupby("manufacturer_id").size(),
        "critical_12m": h[(h.severity == "critical") & (h.t >= cutoff - pd.DateOffset(months=12))].groupby("manufacturer_id").size(),
        "alert_months": g.t.nunique(),
        "span_months": (last - g.t.min()).dt.days / 30.4,
        "share_injectable": g.dosage_form.apply(lambda s: s.isin(["Injection", "IV fluid"]).mean()),
        "share_liquid": g.dosage_form.apply(lambda s: s.isin(["Syrup", "Suspension", "Oral solution / drops"]).mean()),
        "state_hp": g.state.first().eq("Himachal Pradesh").astype(int),
        "state_uk": g.state.first().eq("Uttarakhand").astype(int),
        "state_gj": g.state.first().eq("Gujarat").astype(int),
    }).fillna(0)
    fut = df[(df.t >= cutoff) & (df.t < cutoff + pd.DateOffset(months=HORIZON))].manufacturer_id.unique()
    f["label"] = f.index.isin(fut).astype(int)
    f["cutoff"] = cutoff
    return f


def _at_k(y, score, k):
    order = np.argsort(-np.asarray(score), kind="stable")[:k]
    y = np.asarray(y)
    return {"precision": round(float(y[order].mean()), 3), "recall": round(float(y[order].sum() / max(y.sum(), 1)), 3)}


def factory_risk() -> dict:
    df = _findings()
    train_cut = pd.date_range("2021-01-01", "2025-09-01", freq="MS")
    test_cut = pd.Timestamp("2026-03-01")
    train = pd.concat([factory_features(df, t) for t in train_cut])
    test = factory_features(df, test_cut)
    model = HistGradientBoostingClassifier(max_iter=250, learning_rate=0.05, max_leaf_nodes=15, l2_regularization=1.0,
                                           random_state=C.SEED).fit(train[FACTORY_FEATURES], train.label)
    p = model.predict_proba(test[FACTORY_FEATURES])[:, 1]
    rng = np.random.default_rng(C.SEED)
    scores = {
        "Attention model (ML)": p,
        "Most past failures": test.n_total.values + 1e-3 * test.n_12m.values,
        "Most recent failure": -test.months_since_last.values,
        "Random": rng.random(len(test)),
    }
    res = {}
    for name, s in scores.items():
        res[name] = {"auc": round(float(roc_auc_score(test.label, s)), 3), "top50": _at_k(test.label, s, 50),
                     "top100": _at_k(test.label, s, 100), "top200": _at_k(test.label, s, 200)}
    # confound check: is the model only learning which states are sampled most? Compare inside and outside them,
    # and against a baseline that knows nothing but the unit's state.
    heavy = (test.state_hp + test.state_uk + test.state_gj).astype(bool).values
    state_only = HistGradientBoostingClassifier(max_iter=100, random_state=C.SEED).fit(
        train[["state_hp", "state_uk", "state_gj"]], train.label).predict_proba(test[["state_hp", "state_uk", "state_gj"]])[:, 1]
    confound = {"state_only_baseline_auc": round(float(roc_auc_score(test.label, state_only)), 3), "groups": []}
    for label, m in [("units in HP, Uttarakhand, Gujarat (most sampled)", heavy), ("units in all other states", ~heavy)]:
        y = test.label.values[m]
        confound["groups"].append({"group": label, "units": int(m.sum()), "base_rate": round(float(y.mean()), 3),
                                   "model_auc": round(float(roc_auc_score(y, p[m])), 3),
                                   "most_recent_failure_auc": round(float(roc_auc_score(y, -test.months_since_last.values[m])), 3)})
    # ranking for the latest month: who to inspect next (Sep 2026 onwards)
    latest = factory_features(df, df.t.max() + pd.DateOffset(months=1))
    latest["risk"] = model.predict_proba(latest[FACTORY_FEATURES])[:, 1]
    con = duckdb.connect(str(C.WAREHOUSE_DB), read_only=True)
    names = con.execute("select supplier_key as manufacturer_id, canonical_name, state from dim_supplier").df().set_index("manufacturer_id")
    con.close()
    rank = latest.join(names).sort_values("risk", ascending=False)
    rank["why"] = [f"{int(r.n_12m)} failures in 12 months, {int(r.critical_12m)} critical; last {r.months_since_last:.0f} months ago; "
                   f"{int(r.products)} products affected" for r in rank.itertuples()]
    joblib.dump(model, C.ARTIFACTS / "factory_risk.joblib")
    # every unit's score, for the buyer/regulator view of the lookup API (never shown on public pages)
    rank.reset_index()[["manufacturer_id", "risk"]].round(4).to_csv(C.ARTIFACTS / "attention_scores.csv", index=False)
    base = test.label.mean()
    return {
        "test": {"cutoff": str(test_cut.date()), "horizon_months": HORIZON, "universe": int(len(test)),
                 "positives": int(test.label.sum()), "base_rate": round(float(base), 3), "results": res, "confound": confound},
        "train_rows": int(len(train)),
        "inspect_next": rank.head(60).reset_index()[["manufacturer_id", "canonical_name", "state", "risk", "n_total", "n_12m",
                                                     "critical_12m", "months_since_last", "why"]].round(3).to_dict(orient="records"),
        "as_of": str((df.t.max() + pd.DateOffset(months=1)).date()),
    }


def batch_risk() -> dict:
    erp = sqlite3.connect(C.ERP_DB)
    b = pd.read_sql("""select b.batch_id, b.buyer_id, b.supplier_id, b.item_id, b.received_at, b.sim_true_quality,
                              s.manufacturer_id, i.dosage_form, i.therapeutic_class
                       from batch b join supplier s using(supplier_id) join item i using(item_id)""", erp)
    b = b[~b.batch_id.str.contains("-L") & b.sim_true_quality.notna() & b.received_at.notna()]   # live demo batches have no outcome yet
    b["received_at"] = pd.to_datetime(b.received_at, format="ISO8601")
    df = _findings()
    nat = df.groupby("manufacturer_id")
    b = b.sort_values("received_at").reset_index(drop=True)

    def hits(mid, t, months=12, critical=False):
        if not isinstance(mid, str) or mid not in nat.groups:
            return 0
        g = nat.get_group(mid)
        m = (g.t < t) & (g.t >= t - pd.DateOffset(months=months))
        if critical:
            m &= g.severity.eq("critical")
        return int(m.sum())

    b["nat_12m"] = [hits(m, t) for m, t in zip(b.manufacturer_id, b.received_at)]
    b["nat_crit_12m"] = [hits(m, t, critical=True) for m, t in zip(b.manufacturer_id, b.received_at)]
    b["nat_total"] = [hits(m, t, months=120) for m, t in zip(b.manufacturer_id, b.received_at)]
    b["no_national_record"] = b.manufacturer_id.isna().astype(int)
    # the buyer's own earlier failures with this supplier (known at receipt time)
    b["fail"] = (b.sim_true_quality != "ok").astype(int)
    own = []
    seen: dict[tuple, list] = {}
    for r in b.itertuples():
        own.append(sum(1 for t in seen.get((r.buyer_id, r.supplier_id), []) if t < r.received_at - pd.Timedelta(days=30)))
        if r.fail:
            seen.setdefault((r.buyer_id, r.supplier_id), []).append(r.received_at)
    b["own_failures"] = own
    X = pd.get_dummies(b[["nat_12m", "nat_crit_12m", "nat_total", "no_national_record", "own_failures", "dosage_form", "therapeutic_class"]],
                       columns=["dosage_form", "therapeutic_class"], dtype=float)
    tr = b.received_at < "2026-01-01"
    model = HistGradientBoostingClassifier(max_iter=200, learning_rate=0.05, max_leaf_nodes=15, random_state=C.SEED).fit(X[tr], b.fail[tr])
    b["risk_score"] = model.predict_proba(X)[:, 1]
    te = b[~tr]
    rng = np.random.default_rng(C.SEED)
    k = int(0.3 * len(te))
    strategies = {"DawaDrishti risk order": te.risk_score.values, "First in, first out": -te.received_at.astype("int64").values,
                  "Random": rng.random(len(te))}
    res = {n: {"auc": round(float(roc_auc_score(te.fail, s)), 3), "caught_in_first_30pct": _at_k(te.fail, s, k)["recall"]}
           for n, s in strategies.items()}
    con = sqlite3.connect(C.ERP_DB)
    con.executemany("update batch set risk_score = ? where batch_id = ?", list(zip(b.risk_score.round(4), b.batch_id)))
    con.commit()
    con.close()
    joblib.dump({"model": model, "columns": list(X.columns)}, C.ARTIFACTS / "batch_risk.joblib")
    return {"test": {"period": "2026-01 to 2026-08", "batches": int(len(te)), "failed": int(te.fail.sum()),
                     "lab_capacity_first": "30% of batches", "results": res}}


def run_all() -> dict:
    out = {"factory": factory_risk(), "batch": batch_risk()}
    (C.ARTIFACTS / "risk.json").write_text(json.dumps(out, indent=1, default=str))
    return out


def main():
    out = run_all()
    t = out["factory"]["test"]
    print("  confound:", t["confound"])
    print(f"factory risk: cutoff {t['cutoff']}, {t['universe']} manufacturers, {t['positives']} failed in next 6 months (base {t['base_rate']})")
    for n, r in t["results"].items():
        print(f"  {n:24s} AUC {r['auc']}  top50 precision {r['top50']['precision']} recall {r['top50']['recall']}  top200 recall {r['top200']['recall']}")
    print("inspect next:", [(x["canonical_name"], x["risk"]) for x in out["factory"]["inspect_next"][:5]])
    bt = out["batch"]["test"]
    print(f"batch risk: {bt['batches']} test batches, {bt['failed']} failed")
    for n, r in bt["results"].items():
        print(f"  {n:24s} AUC {r['auc']}  failures caught in first 30% of tests: {r['caught_in_first_30pct']}")


if __name__ == "__main__":
    main()
