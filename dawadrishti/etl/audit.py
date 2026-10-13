"""Extraction audit: how accurately does the PDF parser read CDSCO alerts?

The 2017-2018 records exist only as PDFs. For later months CDSCO publishes both a PDF and structured portal JSON,
so we parse those PDFs too and compare them with the portal, row by row, matched on batch number.

  row recall      share of portal rows (in the audited PDFs' months) that the PDF parser found
  row precision   share of parsed PDF rows that match a portal row
  field agreement for matched rows, share where each field agrees after light normalisation

Run: python -m dawadrishti.etl.audit  ->  artifacts/extraction_audit.json
"""
from __future__ import annotations

import contextlib
import io
import json
import re

import pandas as pd
from rapidfuzz import fuzz

from .. import config as C
from . import clean, parse_pdf
from .stage import load_portal


def _present(v) -> bool:
    return not (v is None or (isinstance(v, float) and pd.isna(v))) and str(v).strip().lower() not in ("", "nan", "none")


def _norm(s) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s or "").lower())


def _date(s) -> str:
    """'Sep-2024', '09/2024', '2024-09', 'SEP.24' -> '2024-09' where possible."""
    t = re.sub(r"\s+", "", str(s or "")).upper().rstrip(".,;")
    m = re.match(r"^(\d{4})-(\d{2})", t)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    mon = {m: i for i, m in enumerate(["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"], 1)}
    m = re.search(r"([A-Z]{3})[A-Z]*[\s./-]*'?(\d{2,4})", t)
    if m and m.group(1) in mon:
        y = m.group(2)
        return f"{'20' + y if len(y) == 2 else y}-{mon[m.group(1)]:02d}"
    m = re.search(r"(\d{1,2})[./-](\d{2,4})$", t) or re.search(r"\d{1,2}[./-](\d{1,2})[./-](\d{2,4})", t)
    if m:
        mm, y = m.group(1), m.group(2)
        return f"{'20' + y if len(y) == 2 else y}-{int(mm):02d}"
    m = re.search(r"(\d{4})-(\d{2})", t)
    return f"{m.group(1)}-{m.group(2)}" if m else t


FIELDS = {
    "product_name": lambda a, b: fuzz.token_set_ratio(str(a).lower(), str(b).lower()) >= 90,
    "manufacturer (name)": lambda a, b: entities_same(a, b),
    "state (derived)": lambda a, b: clean.state_of(a)[0] == clean.state_of(b)[0],
    "nsq_result": lambda a, b: fuzz.token_set_ratio(str(a).lower(), str(b).lower()) >= 85,
    "mfg_date": lambda a, b: _date(a) == _date(b),
    "exp_date": lambda a, b: _date(a) == _date(b),
}
SOURCE_COL = {"manufacturer (name)": "manufacturer", "state (derived)": "manufacturer"}


def entities_same(a, b) -> bool:
    from .entities import score
    return score(clean.name_key(clean.split_manufacturer(a)[0]), clean.name_key(clean.split_manufacturer(b)[0])) >= 92


def run() -> dict:
    with contextlib.redirect_stdout(io.StringIO()):
        pdf = parse_pdf.parse_all(months_before="2100-01")
    portal = load_portal()
    pdf = pdf[pdf.alert_month >= portal.alert_month.min()].copy()
    months = sorted(pdf.alert_month.unique())
    pdf["b"] = pdf.batch_no.map(_norm)
    portal["b"] = portal.batch_no.map(_norm)
    # the PDF for a month can be published under a neighbouring month on the portal; allow +-1 month
    near = portal[portal.alert_month.isin(set(months) | {str((pd.Period(m) + k)) for m in months for k in (-1, 1)})]
    pool = near.groupby("b")
    matched, used = [], set()
    for r in pdf.itertuples():
        if len(r.b) < 3 or r.b not in pool.groups:
            continue
        cands = near.loc[pool.groups[r.b]]
        cands = cands.assign(sim=[fuzz.token_set_ratio(str(r.product_name).lower(), str(p).lower()) for p in cands.product_name])
        c = cands.sort_values("sim", ascending=False).iloc[0]
        if c.sim < 60 or c.name in used:
            continue
        used.add(c.name)
        matched.append((r, c))
    # compare like with like: a central-lab PDF against the portal's CDSCO-lab rows for that month, a state PDF against state rows
    src = portal.reporting_source.fillna("").str.lower()
    portal["kind"] = ["central" if ("cdsco" in x or "central" in x) else "state" if "state" in x else "other" for x in src]
    pdf_kind = pdf.assign(kind=pdf.reporting_source.map({"CDSCO lab": "central", "State lab": "state"}))
    covered = set(zip(pdf_kind.alert_month, pdf_kind.kind))
    in_months = portal[pd.Series([(m, k) in covered for m, k in zip(portal.alert_month, portal.kind)], index=portal.index) & ~portal.source.eq("portal-spurious")]
    fields = {}
    for f, same in FIELDS.items():
        col = SOURCE_COL.get(f, f)
        pairs = [(getattr(r, col, None), c[col]) for r, c in matched if _present(getattr(r, col, None)) and _present(c[col])]
        ok = [bool(same(a, b)) for a, b in pairs]
        fields[f] = {"agreement": round(sum(ok) / len(ok), 3) if ok else None, "compared": len(ok),
                     "missing_in_pdf": sum(not _present(getattr(r, col, None)) for r, _ in matched),
                     "examples_of_disagreement": [{"pdf": str(a)[:90], "portal": str(b)[:90]} for (a, b), k in zip(pairs, ok) if not k][:5]}
    per_doc = pdf.groupby("source_doc").size().to_dict()
    out = {
        "audited_months": months, "pdf_documents": len(per_doc), "pdf_rows": int(len(pdf)),
        "portal_rows_in_those_months": int(len(in_months)), "matched_rows": len(matched),
        "row_precision": round(len(matched) / len(pdf), 3) if len(pdf) else None,
        "row_recall": round(len({c.name for _, c in matched} & set(in_months.index)) / len(in_months), 3) if len(in_months) else None,
        "fields": fields,
        "note": "Row recall is a lower bound: a PDF month and a portal month do not always hold the same set of alerts.",
    }
    (C.ARTIFACTS / "extraction_audit.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    return out


def main():
    out = run()
    print({k: v for k, v in out.items() if k != "fields"})
    for f, v in out["fields"].items():
        print(f"  {f:22s} agreement {v['agreement']}  (n={v['compared']}, missing in pdf {v['missing_in_pdf']})  e.g. {v['examples_of_disagreement'][:5]}")


if __name__ == "__main__":
    main()
