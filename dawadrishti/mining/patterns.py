"""Data mining on the REAL national NSQ data (warehouse view v_findings).

  repeat failures    recurrence: after a failure, how often and how soon does the same unit fail again?
  association rules  FP-Growth over (dosage form, class, state, failure, severity, lab type)
  clustering         k-means on manufacturer failure profiles -> named risk archetypes
  anomalies          monthly spikes per state and per therapeutic class vs their own trailing 12 months
  geography          failures, manufacturers and critical share by state
  trends             national monthly counts by severity
"""
from __future__ import annotations

import json

import duckdb
import numpy as np
import pandas as pd
from mlxtend.frequent_patterns import association_rules, fpgrowth
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from .. import config as C


def findings() -> pd.DataFrame:
    con = duckdb.connect(str(C.WAREHOUSE_DB), read_only=True)
    df = con.execute("select * from v_findings").df()
    con.close()
    df["month_ts"] = pd.to_datetime(df.month + "-01")
    return df


def repeat_failures(df: pd.DataFrame, top: int = 40) -> dict:
    d = df[df.manufacturer_id.notna()].sort_values("month_ts")
    g = d.groupby(["manufacturer_id", "manufacturer", "state"])
    prof = g.agg(findings=("finding_id", "count"), first=("month", "min"), last=("month", "max"),
                 products=("generic_name", "nunique"), critical=("severity", lambda s: int((s == "critical").sum())),
                 months_with_alerts=("month", "nunique")).reset_index()
    # recurrence: for each alert month of a firm, is there another alert in the next 12 months?
    months = d.groupby("manufacturer_id").month_ts.apply(lambda s: sorted(set(s)))
    gaps, rec = [], []
    cutoff = df.month_ts.max() - pd.DateOffset(months=12)
    for ms in months:
        for i, m in enumerate(ms):
            if m <= cutoff:
                rec.append(any(m < x <= m + pd.DateOffset(months=12) for x in ms[i + 1:]))
        gaps += [(b - a).days / 30.4 for a, b in zip(ms, ms[1:])]
    repeat = prof[prof.months_with_alerts >= 2]
    return {
        "manufacturers": int(len(prof)),
        "repeat_manufacturers": int(len(repeat)),
        "repeat_share_of_findings": round(float(repeat.findings.sum() / prof.findings.sum()), 4),
        "recurrence_12m": round(float(np.mean(rec)), 4),
        "median_months_between_failures": round(float(np.median(gaps)), 1) if gaps else None,
        "top": prof.sort_values(["findings", "critical"], ascending=False).head(top).to_dict(orient="records"),
    }


def assoc_rules(df: pd.DataFrame, min_support=0.02, min_lift=1.3) -> list[dict]:
    items = pd.DataFrame({
        "form": "form=" + df.dosage_form, "class": "class=" + df.therapeutic_class, "state": "state=" + df.state,
        "failure": "failure=" + df.primary_failure, "severity": "severity=" + df.severity,
        "lab": "lab=" + df.reporting_source.fillna("?"),
    })
    onehot = pd.get_dummies(items, prefix="", prefix_sep="").astype(bool)
    onehot = onehot.T.groupby(level=0).any().T
    fi = fpgrowth(onehot, min_support=min_support, use_colnames=True)
    rules = association_rules(fi, metric="lift", min_threshold=min_lift)
    rules = rules[rules.consequents.apply(lambda c: len(c) == 1 and next(iter(c)).split("=")[0] in ("failure", "severity"))]
    rules = rules[rules.antecedents.apply(lambda a: not any(x.split("=")[0] in ("failure", "severity") for x in a))]
    rules = rules.sort_values(["lift", "confidence"], ascending=False).head(25)
    return [{"if": sorted(r.antecedents), "then": next(iter(r.consequents)), "support": round(r.support, 4),
             "confidence": round(r.confidence, 3), "lift": round(r.lift, 2)} for r in rules.itertuples()]


def clusters(df: pd.DataFrame, k: int = 4) -> dict:
    d = df[df.manufacturer_id.notna()]
    g = d.groupby(["manufacturer_id", "manufacturer"])
    feat = pd.DataFrame({
        "findings": g.finding_id.count(), "products": g.generic_name.nunique(), "months": g.month.nunique(),
        "critical_share": g.severity.apply(lambda s: (s == "critical").mean()),
        "major_share": g.severity.apply(lambda s: (s == "major").mean()),
        "injectable_share": g.dosage_form.apply(lambda s: s.isin(["Injection", "IV fluid"]).mean()),
        "liquid_share": g.dosage_form.apply(lambda s: s.isin(["Syrup", "Suspension", "Oral solution / drops"]).mean()),
    })
    X = StandardScaler().fit_transform(np.log1p(feat[["findings", "products", "months"]]).join(feat.drop(columns=["findings", "products", "months"])))
    km = KMeans(n_clusters=k, n_init=10, random_state=C.SEED).fit(X)
    feat["cluster"] = km.labels_
    cent = feat.groupby("cluster").mean()

    def name(c):
        r = cent.loc[c]
        if r.critical_share > 0.35:
            return "Mostly critical failures"
        if r.findings >= cent.findings.max() * 0.6:
            return "Many failures on record"
        if r.injectable_share > 0.4:
            return "Mostly injectable failures"
        if r.findings <= 1.6:
            return "One failure on record"
        return "A few failures on record"

    names = {c: name(c) for c in cent.index}
    feat["archetype"] = feat.cluster.map(names)
    summary = feat.groupby("archetype").agg(manufacturers=("findings", "size"), avg_findings=("findings", "mean"),
                                            avg_critical_share=("critical_share", "mean"), avg_products=("products", "mean")).round(2)
    pts = feat.reset_index().sample(min(600, len(feat)), random_state=1)
    return {"summary": summary.reset_index().to_dict(orient="records"),
            "points": pts[["manufacturer", "findings", "critical_share", "products", "archetype"]].round(3).to_dict(orient="records")}


def anomalies(df: pd.DataFrame, z: float = 3.0, min_count: int = 8) -> list[dict]:
    out = []
    for dim in ["state", "therapeutic_class"]:
        m = df.groupby([dim, "month_ts"]).size().unstack(0).fillna(0).asfreq("MS", fill_value=0)
        base_mean = m.shift(1).rolling(12, min_periods=6).mean()
        base_std = m.shift(1).rolling(12, min_periods=6).std().clip(lower=1.5)
        score = (m - base_mean) / base_std
        for (t, key), s in score.stack().items():
            if s >= z and m.loc[t, key] >= min_count:
                out.append({"dimension": dim, "value": key, "month": t.strftime("%Y-%m"), "count": int(m.loc[t, key]),
                            "expected": round(float(base_mean.loc[t, key]), 1), "z": round(float(s), 1)})
    return sorted(out, key=lambda x: (x["month"], -x["z"]), reverse=True)


def geography(df: pd.DataFrame) -> list[dict]:
    g = df.groupby("state").agg(findings=("finding_id", "count"), manufacturers=("manufacturer_id", "nunique"),
                                critical=("severity", lambda s: int((s == "critical").sum())))
    g["critical_share"] = (g.critical / g.findings).round(3)
    g["share_of_india"] = (g.findings / g.findings.sum()).round(4)
    return g.sort_values("findings", ascending=False).reset_index().to_dict(orient="records")


def trends(df: pd.DataFrame) -> dict:
    t = df.groupby(["month", "severity"]).size().unstack(fill_value=0)
    by_fail = df.groupby(["year", "primary_failure"]).size().unstack(fill_value=0)
    return {"monthly": t.reset_index().to_dict(orient="records"),
            "by_year_failure": by_fail.reset_index().to_dict(orient="records"),
            "forms": df.dosage_form.value_counts().to_dict(), "classes": df.therapeutic_class.value_counts().to_dict(),
            "failures": df.primary_failure.value_counts().to_dict(), "severity": df.severity.value_counts().to_dict(),
            "sources": df.reporting_source.value_counts().to_dict(), "spurious": int(df.is_spurious.sum())}


def run_all() -> dict:
    df = findings()
    out = {"as_of": df.month.max(), "since": df.month.min(), "findings": int(len(df)),
           "repeat": repeat_failures(df), "rules": assoc_rules(df), "clusters": clusters(df),
           "anomalies": anomalies(df)[:40], "geography": geography(df), "trends": trends(df)}
    (C.ARTIFACTS / "data_mining.json").write_text(json.dumps(out, indent=1, default=str))
    return out


def main():
    out = run_all()
    r = out["repeat"]
    print(f"{out['findings']} findings {out['since']}..{out['as_of']}; {r['manufacturers']} manufacturers, "
          f"{r['repeat_manufacturers']} repeat ({r['repeat_share_of_findings']:.0%} of findings); "
          f"12-month recurrence {r['recurrence_12m']:.0%}; median gap {r['median_months_between_failures']} months")
    for x in out["rules"][:8]:
        print(f"  rule: {' + '.join(x['if'])} -> {x['then']}  conf {x['confidence']} lift {x['lift']} supp {x['support']}")
    print("clusters:", out["clusters"]["summary"])
    print("anomalies (latest):", out["anomalies"][:5])
    print("geo top:", out["geography"][:4])


if __name__ == "__main__":
    main()
