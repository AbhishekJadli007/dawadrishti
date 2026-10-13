"""Ask DawaDrishti: a plain-English question -> one of a fixed set of query templates -> a table.

The model never writes SQL. It only chooses a template and fills its parameters, and every parameter is checked
against the values that exist in the warehouse (states, dosage forms, classes, molecules, months) before the query
runs with bound parameters. Without GEMINI_API_KEY, a keyword parser does the same choosing, so the box always works.
Answers are tables of published records; the model writes no prose about any manufacturer.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache

import duckdb

from .. import config as C

# name -> (description shown to the model and the user, SQL with $named parameters, data label)
TEMPLATES: dict[str, tuple[str, str, str]] = {
    "top_units": (
        "Manufacturing units with the most failed batches, optionally filtered by state, dosage form, class, molecule, period, severity",
        """select manufacturer, state, count(*) as failed_batches, sum(case when severity='critical' then 1 else 0 end) as critical,
                  min(month) as first_alert, max(month) as latest_alert
           from v_findings where manufacturer_id is not null {where} group by 1,2 order by failed_batches desc limit $limit""", "real"),
    "by_state": (
        "Failed batches by the manufacturer's state, optionally filtered by dosage form, class, molecule, period, severity",
        """select state, count(*) as failed_batches, count(distinct manufacturer_id) as units,
                  round(100.0*avg(case when severity='critical' then 1 else 0 end),1) as critical_pct
           from v_findings where true {where} group by 1 order by failed_batches desc limit $limit""", "real"),
    "failure_types": (
        "What the failures were (assay, dissolution, sterility, ...), optionally for a state, dosage form, class, molecule, period",
        """select primary_failure, severity, count(*) as failed_batches from v_findings where true {where}
           group by 1,2 order by failed_batches desc limit $limit""", "real"),
    "trend": (
        "Failed batches per year, optionally filtered by state, dosage form, class, molecule, severity",
        """select year, count(*) as failed_batches, sum(case when severity='critical' then 1 else 0 end) as critical
           from v_findings where true {where} group by 1 order by 1""", "real"),
    "repeat_units": (
        "Units with at least $min_alerts alerts in the last $months months, optionally in a state",
        """select manufacturer, state, count(*) as alerts_in_window, count(distinct month) as alert_months, max(month) as latest_alert
           from v_findings where manufacturer_id is not null
             and month >= strftime(date_trunc('month', (select max(cast(month || '-01' as date)) from v_findings)) - to_months($months - 1), '%Y-%m')
             {where} group by 1,2 having count(*) >= $min_alerts order by alerts_in_window desc limit $limit""", "real"),
    "spurious": (
        "Batches confirmed spurious (fake), optionally by period, state or molecule",
        """select month, generic_name, dosage_form, reporting_lab, state from v_findings where is_spurious {where}
           order by month desc limit $limit""", "real"),
    "buyers_ordering_flagged": (
        "Units with 5+ national alerts that the simulated buyers still order from",
        """select s.canonical_name as manufacturer, s.state, s.national_findings, count(distinct e.case_id) as orders,
                  count(distinct e.buyer_id) as buyers
           from v_events e join dim_supplier s on e.supplier_key = s.supplier_key
           where e.activity = 'PO created' and s.national_findings >= 5 group by 1,2,3 order by s.national_findings desc limit $limit""",
        "simulated buyers, real alert counts"),
    "lab_turnaround": (
        "Median lab turnaround at each simulated buyer",
        """with t as (select case_id, buyer, min(case when activity='Sent to lab' then ts end) as sent,
                             min(case when activity='Report received' then ts end) as rep from v_events group by 1,2)
           select buyer, round(median(date_diff('hour', sent, rep))/24.0, 1) as median_lab_days, count(*) as cases
           from t group by 1 order by median_lab_days""", "simulated"),
    "issued_before_clearance": (
        "Cases at each simulated buyer where stock was issued before quality clearance",
        """with t as (select case_id, buyer, min(case when activity='Issued' then ts end) as issued,
                             min(case when activity='Cleared' then ts end) as cleared,
                             max(case when activity='Held' then 1 else 0 end) as failed from v_events group by 1,2)
           select buyer, count(*) as cases, sum(failed) as of_which_failed from t
           where issued is not null and (cleared is null or issued < cleared) group by 1 order by cases desc""", "simulated"),
}

FILTERS = {  # parameter -> SQL condition on v_findings
    "state": "state = $state", "dosage_form": "dosage_form = $dosage_form", "therapeutic_class": "therapeutic_class = $therapeutic_class",
    "molecule": "generic_name ilike '%' || $molecule || '%'", "since": "month >= $since", "until": "month <= $until",
    "severity": "severity = $severity",
}
PRESETS = {
    "Which units have failed most often nationally?": ("top_units", {}),
    "Which states make the most failing drugs?": ("by_state", {}),
    "How do injections fail?": ("failure_types", {"dosage_form": "Injection"}),
    "How many cough and cold medicines failed each year?": ("trend", {"therapeutic_class": "Cough / cold / allergy"}),
    "Which units in Himachal Pradesh had 3+ alerts in the last 12 months?": ("repeat_units", {"state": "Himachal Pradesh", "min_alerts": 3, "months": 12}),
    "Which drugs were found to be spurious (fakes)?": ("spurious", {}),
    "Which nationally failing units are the simulated buyers still ordering from?": ("buyers_ordering_flagged", {}),
    "Where were batches issued before quality clearance? (simulated buyers)": ("issued_before_clearance", {}),
}


@lru_cache(maxsize=1)
def vocab() -> dict:
    con = duckdb.connect(str(C.WAREHOUSE_DB), read_only=True)
    col = lambda c: [r[0] for r in con.execute(f"select distinct {c} from v_findings where {c} is not null order by 1").fetchall()]
    v = {"state": col("state"), "dosage_form": col("dosage_form"), "therapeutic_class": col("therapeutic_class"),
         "severity": ["critical", "major", "minor"],
         "molecule": [r[0] for r in con.execute("""select lower(generic_name) g from v_findings where length(generic_name) between 4 and 30
                                                   group by 1 having count(*) >= 3 order by count(*) desc limit 800""").fetchall()],
         "months": [con.execute("select min(month), max(month) from v_findings").fetchone()]}
    con.close()
    return v


def validate(template: str, params: dict) -> dict:
    if template not in TEMPLATES:
        raise ValueError(f"Unknown template {template!r}")
    v, out = vocab(), {}
    for k, val in (params or {}).items():
        if val in (None, "", []):
            continue
        if k in ("state", "dosage_form", "therapeutic_class", "severity"):
            match = next((x for x in v[k] if x.lower() == str(val).lower()), None)
            if not match:
                raise ValueError(f"{k} must be one of the values in the data, not {val!r}")
            out[k] = match
        elif k == "molecule":
            m = re.sub(r"[^a-z0-9 \-]", "", str(val).lower()).strip()
            if len(m) < 3:
                raise ValueError("molecule name too short")
            out[k] = m
        elif k in ("since", "until"):
            m = re.fullmatch(r"(\d{4})(?:-(\d{2}))?", str(val))
            if not m:
                raise ValueError(f"{k} must be YYYY or YYYY-MM")
            out[k] = f"{m.group(1)}-{m.group(2) or ('01' if k == 'since' else '12')}"
        elif k in ("min_alerts", "months", "limit"):
            out[k] = max(1, min(int(val), 120 if k == "months" else 500))
        else:
            raise ValueError(f"Unknown parameter {k!r}")
    out.setdefault("limit", 25)
    if template == "repeat_units":
        out.setdefault("min_alerts", 3)
        out.setdefault("months", 12)
    return out


def build(template: str, params: dict) -> tuple[str, dict]:
    _, sql, _ = TEMPLATES[template]
    conds = [FILTERS[k] for k in params if k in FILTERS]
    where = "".join(f" and {c}" for c in conds)
    sql = re.sub(r"\s+", " ", sql.replace("{where}", where)).strip()
    used = {k: v for k, v in params.items() if f"${k}" in sql}
    return sql, used


def run(template: str, params: dict) -> dict:
    p = validate(template, params)
    sql, bound = build(template, p)
    con = duckdb.connect(str(C.WAREHOUSE_DB), read_only=True)
    try:
        cur = con.execute(sql, bound)
        cols = [d[0] for d in cur.description]
        rows = [list(r) for r in cur.fetchall()]
    finally:
        con.close()
    return {"template": template, "description": TEMPLATES[template][0], "data": TEMPLATES[template][2], "params": p,
            "sql": sql, "columns": cols, "rows": rows}


# ------------------------------------------------------------------ choosing a template
def parse_rules(q: str) -> tuple[str, dict]:
    """Keyword parser used when no LLM key is set."""
    t, v, p = q.lower(), vocab(), {}
    for s in sorted(v["state"], key=len, reverse=True):
        if s.lower() in t and s not in ("Unknown", "Outside India"):
            p["state"] = s
            break
    forms = {"injection": "Injection", "injectable": "Injection", "tablet": "Tablet", "capsule": "Capsule", "syrup": "Syrup",
             "suspension": "Suspension", "iv fluid": "IV fluid", "ointment": "Cream / ointment / gel", "cream": "Cream / ointment / gel",
             "vaccine": "Vaccine / biological", "eye drop": "Oral solution / drops"}
    for k, f in forms.items():
        if k in t and f in v["dosage_form"]:
            p["dosage_form"] = f
            break
    classes = {"antibiotic": "Antibiotic / anti-infective", "cough": "Cough / cold / allergy", "diabet": "Antidiabetic",
               "vitamin": "Vitamins / minerals / nutrition", "pain": "Analgesic / anti-inflammatory", "fever": "Analgesic / anti-inflammatory",
               "heart": "Cardiovascular", "blood pressure": "Cardiovascular", "malaria": "Antimalarial / antiparasitic"}
    for k, c in classes.items():
        if k in t and c in v["therapeutic_class"]:
            p["therapeutic_class"] = c
            break
    for m in v["molecule"]:
        if len(m) >= 5 and re.search(rf"\b{re.escape(m)}\b", t):
            p["molecule"] = m
            break
    if "critical" in t:
        p["severity"] = "critical"
    y = re.search(r"\b(since|after|from)\s+(20\d\d)\b", t)
    if y:
        p["since"] = y.group(2)
    elif (y := re.search(r"\bin\s+(20\d\d)\b", t)):
        p["since"], p["until"] = y.group(1), y.group(1)
    if re.search(r"spurious|fake|counterfeit", t):
        return "spurious", p
    if re.search(r"turnaround|lab days|how long.*lab", t):
        return "lab_turnaround", {}
    if re.search(r"before (quality )?clearance|issued before", t):
        return "issued_before_clearance", {}
    if re.search(r"still order|buyers? .*order", t):
        return "buyers_ordering_flagged", {}
    if re.search(r"repeat|again|\d+\+?\s*(alerts|times|failures)|more than \d", t):
        n = re.search(r"(\d+)\+?\s*(alerts|times|failures)", t)
        mo = re.search(r"last (\d+) months", t)
        return "repeat_units", {**p, "min_alerts": int(n.group(1)) if n else 3, "months": int(mo.group(1)) if mo else 12}
    if re.search(r"each year|per year|over time|trend|by year|every year", t):
        return "trend", p
    if re.search(r"how do|how did|fail on|failure type|what fail|why", t):
        return "failure_types", p
    if re.search(r"which states?|by state|where are|where do", t) and "state" not in p:
        return "by_state", p
    return "top_units", p


def parse_llm(q: str) -> tuple[str, dict]:
    from google import genai
    v = vocab()
    spec = {name: desc for name, (desc, _, _) in TEMPLATES.items()}
    prompt = ("Map the user's question to ONE query template and its parameters. Reply with JSON only: "
              '{"template": name, "params": {...}}.\n'
              f"Templates: {json.dumps(spec)}\n"
              "Parameters (all optional): state, dosage_form, therapeutic_class, severity (exact values from the lists), "
              "molecule (a generic drug name), since/until (YYYY or YYYY-MM), min_alerts, months, limit.\n"
              f"states: {v['state']}\ndosage_form: {v['dosage_form']}\ntherapeutic_class: {v['therapeutic_class']}\n"
              f"Data covers {v['months'][0][0]} to {v['months'][0][1]}.\nQuestion: {q}")
    client = genai.Client(api_key=C.GEMINI_KEY)
    resp = client.models.generate_content(model=C.GEMINI_MODEL, contents=prompt)
    m = re.search(r"\{.*\}", resp.text or "", re.S)
    if not m:
        raise ValueError("The model did not return a template choice")
    j = json.loads(m.group(0))
    return j["template"], j.get("params") or {}


def ask(question: str) -> dict:
    q = question.strip()
    if q in PRESETS:
        t, p = PRESETS[q]
        src = "preset"
    elif C.GEMINI_KEY:
        t, p = parse_llm(q)
        src = f"template chosen by {C.GEMINI_MODEL}"
    else:
        t, p = parse_rules(q)
        src = "template chosen by keyword rules (no LLM key set)"
    return {"question": q, "source": src, **run(t, p)}
