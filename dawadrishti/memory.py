"""The national quality memory: one lookup that any buyer's ERP (DVDMS, e-Aushadhi, a state corporation's system) can call.

    lookup(manufacturer, view="public" | "buyer")

Public view   the public record only: alerts as published by CDSCO, with dates, labs and batch numbers, the data's
              as-of date, what the data does not contain, and how to request a correction. No predicted score.
              The text describes records; it never characterises a firm.
Buyer view    adds the graded response (what a buyer should do now, by severity and recency), the model's
              "future regulatory attention" score with its evaluation, and alternatives from the buyer network's
              supplier masters.

Identity is resolved to a manufacturing unit (firm + state) and rolled up to the firm, so the answer says how the
name was matched and which other units of the firm are on record.
"""
from __future__ import annotations

import datetime as dt
import json
from functools import lru_cache

import duckdb
import pandas as pd
from rapidfuzz import fuzz

from . import config as C
from .etl import clean, entities

CORRECTION_URL = "https://github.com/AbhishekJadli007/dawadrishti/issues/new?template=correction.md"
SOURCE_URL = "https://cdscoonline.gov.in/CDSCO/Drugs"

NOT_CONTAINED = [
    "Batches that were tested and passed. The alerts list failures only, so a failure rate cannot be computed.",
    "Licence suspensions, cancellations, prosecutions or court outcomes. The regulatory-action field is filled only from a cited order.",
    "Whether a failure caused harm to any patient.",
    "The firm's reply or a re-test result, unless CDSCO published it with the alert.",
    "Failures found by state or institutional labs that were never reported to CDSCO's national list.",
    "Sampling effort: states and products that are tested more often appear more often.",
]

RESPONSES = [  # level, label, what the buyer's ERP should do; first matching rule wins
    (3, "Pause new orders", "A critical failure (sterility, contamination, spurious, toxic impurity) in the last 12 months, "
        "or debarment by a buyer. Place no new order without a recorded override; test stock in hand before issue."),
    (2, "Test every batch", "A critical failure 13 to 36 months ago, or 2+ alerts in the last 12 months. "
        "No skip-lot testing: every batch is tested and held until cleared."),
    (1, "Prefer alternatives", "At least one alert in the last 36 months. Normal testing; at equal price and supply, "
        "prefer a supplier with no recent record."),
    (0, "No recent national record", "No alert in the last 36 months. This is absence of a record, not a certificate of quality."),
]


def _wh():
    return duckdb.connect(str(C.WAREHOUSE_DB), read_only=True)


@lru_cache(maxsize=1)
def _data_as_of() -> str:
    con = _wh()
    m = con.execute("select max(month) from v_findings").fetchone()[0]
    con.close()
    return m


@lru_cache(maxsize=1)
def _units() -> pd.DataFrame:
    con = _wh()
    u = con.execute("""select supplier_key as manufacturer_id, canonical_name, state, firm_id, firm_name, national_findings,
                              first_alert, last_alert, critical_findings
                       from dim_supplier where manufacturer_id is not null""").df()
    con.close()
    u["key"] = u.canonical_name.map(clean.name_key)
    return u


@lru_cache(maxsize=1)
def _scores() -> dict:
    p = C.ARTIFACTS / "attention_scores.csv"
    return dict(pd.read_csv(p).values) if p.exists() else {}


def resolve(query: str, state: str | None = None) -> dict:
    """Name (as written on an invoice or tender) -> unit. IDs pass straight through.
    Only a match at or above the auto-merge threshold returns a record; anything weaker returns candidates for a person
    to confirm, because showing one firm's record under another firm's name is the worst error this system can make."""
    u = _units()
    if query in set(u.manufacturer_id):
        return {"manufacturer_id": query, "match": "id", "score": 100.0, "candidates": []}
    k = clean.name_key(query)
    cand = u if not state else u[u.state.eq(state)]
    if cand.empty:
        cand = u
    strict = cand.key.map(lambda x: entities.score(k, x))
    loose = cand.key.map(lambda x: fuzz.token_set_ratio(k, x))       # "sresan pharma" inside "sresan pharma manufacturer"
    rank = pd.DataFrame({"strict": strict, "loose": loose}).assign(best=lambda r: r.max(axis=1)).sort_values("best", ascending=False)
    top = rank.head(5)
    candidates = [{"manufacturer_id": cand.loc[i, "manufacturer_id"], "name": cand.loc[i, "canonical_name"],
                   "state": cand.loc[i, "state"], "alerts": int(cand.loc[i, "national_findings"]), "score": round(float(r.best), 1)}
                  for i, r in top.iterrows() if r.best >= 75]
    if len(rank) and rank.strict.max() >= entities.UNIT_THRESHOLD:
        i = rank.strict.idxmax()
        sc = float(rank.strict.max())
        return {"manufacturer_id": cand.loc[i, "manufacturer_id"], "score": round(sc, 1),
                "match": "exact" if sc == 100 else "fuzzy (automatic)", "candidates": candidates}
    return {"manufacturer_id": None, "match": "needs confirmation" if candidates else "none",
            "score": round(float(rank.best.max()), 1) if len(rank) else 0.0, "candidates": candidates}


def graded_response(findings: pd.DataFrame, as_of: pd.Timestamp, debarred: bool = False) -> dict:
    t = pd.to_datetime(findings.month + "-01") if len(findings) else pd.Series(dtype="datetime64[ns]")
    age = ((as_of - t).dt.days / 30.44) if len(findings) else pd.Series(dtype=float)
    crit = findings.severity.eq("critical") if len(findings) else pd.Series(dtype=bool)
    facts = {"alerts_12m": int((age <= 12).sum()), "alerts_36m": int((age <= 36).sum()),
             "critical_12m": int(((age <= 12) & crit).sum()), "critical_36m": int(((age <= 36) & crit).sum())}
    if debarred or facts["critical_12m"]:
        lvl = 3
    elif facts["critical_36m"] or facts["alerts_12m"] >= 2:
        lvl = 2
    elif facts["alerts_36m"]:
        lvl = 1
    else:
        lvl = 0
    _, label, rule = next(r for r in RESPONSES if r[0] == lvl)
    return {"level": lvl, "label": label, "rule": rule, "facts": facts, "debarred_by_a_buyer": debarred}


def alternatives(generic_name: str | None, exclude_firm: str | None, limit: int = 6) -> list[dict]:
    """Other suppliers of the molecule in the buyer network's supplier masters, ordered by their national record.
    The alerts list only failing firms, so alternatives must come from buyers' masters (simulated here), not from the alerts."""
    if not generic_name:
        return []
    from .erp.schema import connect
    con = connect()
    rows = con.execute("""select distinct s.supplier_id, s.name, s.state, s.manufacturer_id, s.debarred_by
                          from purchase_order p join supplier s using(supplier_id) join item i using(item_id)
                          where lower(i.generic_name) = lower(?)""", (generic_name,)).fetchall()
    con.close()
    u = _units().set_index("manufacturer_id")
    con = _wh()
    as_of = pd.Timestamp(_data_as_of() + "-01")
    out = []
    for r in rows:
        mid = r["manufacturer_id"]
        if mid and mid in u.index and u.loc[mid, "firm_id"] == exclude_firm:
            continue
        f = con.execute("select month, severity from v_findings where manufacturer_id = ?", [mid]).df() if mid else pd.DataFrame(columns=["month", "severity"])
        g = graded_response(f, as_of, bool(r["debarred_by"]))
        out.append({"supplier_id": r["supplier_id"], "name": r["name"], "state": r["state"], "manufacturer_id": mid,
                    "response_level": g["level"], "response": g["label"], "alerts_36m": g["facts"]["alerts_36m"]})
    con.close()
    return sorted(out, key=lambda x: (x["response_level"], x["alerts_36m"], x["name"]))[:limit]


def _bought_item(mid: str) -> str | None:
    """The molecule the buyer network buys most from this unit (from the ERP's purchase orders)."""
    from .erp.schema import connect
    con = connect()
    r = con.execute("""select i.generic_name, count(*) n from purchase_order p join supplier s using(supplier_id)
                       join item i using(item_id) where s.manufacturer_id = ? group by 1 order by n desc limit 1""", (mid,)).fetchone()
    con.close()
    return r[0] if r else None


def lookup(query: str, view: str = "public", state: str | None = None, molecule: str | None = None) -> dict:
    who = resolve(query, state)
    as_of_data = _data_as_of()
    base = {"query": query, "view": view, "data_as_of": as_of_data, "generated_at": dt.date.today().isoformat(),
            "source": "CDSCO 'Not of Standard Quality' and spurious drug alerts (public)", "source_url": SOURCE_URL,
            "data_does_not_contain": NOT_CONTAINED,
            "correction": {"how": "Anyone named can ask for a record to be corrected or annotated with a re-test result "
                                  "or a firm reply. Each request is reviewed against the published alert.", "url": CORRECTION_URL}}
    if not who["manufacturer_id"]:
        statement = (f"\"{query}\" did not match any name in the alerts closely enough to show a record. "
                     "Pick one of the candidates to confirm it." if who["candidates"] else
                     f"No manufacturer matching \"{query}\" appears in CDSCO's national alerts up to {as_of_data}. "
                     "Absence from the alerts is not evidence of quality (see what the data does not contain).")
        return {**base, "identity": who, "record": None, "statement": statement}
    mid = who["manufacturer_id"]
    u = _units().set_index("manufacturer_id")
    unit = u.loc[mid]
    con = _wh()
    f = con.execute("""select month, generic_name, dosage_form, primary_failure, severity, reporting_lab, reporting_source,
                              batch_no, is_spurious, manufacturer_id, state
                       from v_findings where firm_id = ? order by month desc""", [unit.firm_id]).df()
    con.close()
    here = f[f.manufacturer_id.eq(mid)]
    other_units = (f[~f.manufacturer_id.eq(mid)].groupby(["manufacturer_id", "state"]).size().reset_index(name="alerts")
                   .to_dict(orient="records"))
    as_of = pd.Timestamp(as_of_data + "-01") + pd.offsets.MonthEnd(0)
    record = {
        "unit": {"manufacturer_id": mid, "name": unit.canonical_name, "state": unit.state},
        "firm": {"firm_id": unit.firm_id, "name": unit.firm_name, "other_units_on_record": other_units},
        "alerts": int(len(here)), "alerts_all_units": int(len(f)),
        "first_alert": here.month.min() if len(here) else None, "last_alert": here.month.max() if len(here) else None,
        "by_failure": here.primary_failure.value_counts().to_dict(),
        "by_severity": here.severity.value_counts().to_dict(),
        "detected_by": here.reporting_source.value_counts().to_dict(),
        "labs": int(here.reporting_lab.nunique()),
        "entries": here.head(40).drop(columns=["manufacturer_id"]).to_dict(orient="records"),
        "regulatory_action": None,
        "regulatory_action_note": "Not recorded. Filled only from a cited CDSCO or state order.",
    }
    out = {**base, "identity": who, "record": record,
           "statement": (f"{len(here)} published alert{'s' if len(here) != 1 else ''} name this unit "
                         f"({record['first_alert']} to {record['last_alert']}), data as of {as_of_data}.")}
    if view == "buyer":
        from .erp.schema import connect
        c = connect()
        deb = c.execute("select debarred_by, debarred_on from supplier where manufacturer_id = ? and debarred_by is not null",
                        (mid,)).fetchone()
        c.close()
        g = graded_response(here, as_of, bool(deb))
        risk = json.loads((C.ARTIFACTS / "risk.json").read_text())["factory"] if (C.ARTIFACTS / "risk.json").exists() else None
        score = _scores().get(mid)
        out["buyer"] = {
            "graded_response": g, "debarred": dict(deb) if deb else None,
            "future_regulatory_attention": None if score is None else {
                "probability_next_6_months": round(float(score), 3),
                "means": "Estimated chance that this unit appears in CDSCO alerts in the next 6 months. It predicts regulatory "
                         "attention (sampling and testing), which is not the same thing as the unit's true failure rate.",
                "evaluation": {k: v["auc"] for k, v in risk["test"]["results"].items()} if risk else None,
            },
            "alternatives_for": molecule or _bought_item(mid),
            "alternatives": alternatives(molecule or _bought_item(mid), unit.firm_id),
        }
    return out
