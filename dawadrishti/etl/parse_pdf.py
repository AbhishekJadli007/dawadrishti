"""Step 1c of the ETL: extract NSQ records from CDSCO's PDF alerts (used for months the JSON portal lacks).

pdfplumber reads each table; headers are matched to our schema by keywords, because column titles vary
across years ("Manufactured By", "Name & Address of Manufacturer", ...). Rows that span page breaks are merged.
"""
from __future__ import annotations

import re

import pandas as pd
import pdfplumber

from .. import config as C

COLS = {
    "product_name": r"product|drug|name of (the )?drug|vaccine",
    "batch_no": r"batch",
    "mfg_date": r"manufactur\w*\s*date|mfg|date of manufacture",
    "exp_date": r"expir|exp\.",
    "manufacturer": r"manufactured\s*by|name.*address|manufacturer|firm",
    "nsq_result": r"nsq\s*result|result|reason|test|parameter",
    "reporting_lab": r"reported by|laborator|lab",
}


SPACED = re.compile(r"\b(?:[A-Za-z] ){3,}[A-Za-z]\b")


def tidy(text) -> str:
    """Collapse whitespace and re-join letter-spaced words ("P h a r m a" -> "Pharma"), a pdfplumber artefact."""
    t = re.sub(r"\s+", " ", str(text or "")).strip()
    return SPACED.sub(lambda m: m.group(0).replace(" ", ""), t)


def map_header(cells: list) -> dict[int, str]:
    out = {}
    for i, c in enumerate(cells):
        t = re.sub(r"\s+", " ", str(c or "")).lower()
        tight = t.replace(" ", "")          # pdfplumber splits words: "Manufactu ring Date"
        for key, pat in COLS.items():
            if key not in out.values() and (re.search(pat, t) or re.search(pat, tight)):
                # "Manufacturing Date" must not be read as manufacturer
                if key == "manufacturer" and re.search(r"date", t):
                    continue
                out[i] = key
                break
    return out


def parse_pdf(path, doc_id: str, alert_month: str | None, kind: str) -> list[dict]:
    rows, header = [], None
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                for cells in table:
                    if not cells or not any(cells):
                        continue
                    joined = " ".join(str(c or "") for c in cells).lower()
                    if ("batch" in joined and ("product" in joined or "drug" in joined or "manufactur" in joined)):
                        header = map_header(cells)
                        continue
                    if not header or len(header) < 4:
                        continue
                    rec = {k: tidy(cells[i]) for i, k in header.items() if i < len(cells)}
                    first = str(cells[0] or "").strip()
                    if not re.match(r"^\d+\.?$", first) and rows:
                        # continuation of the previous row across a page break
                        for k, v in rec.items():
                            if v:
                                rows[-1][k] = (rows[-1].get(k, "") + " " + v).strip()
                        continue
                    if not rec.get("product_name") or not rec.get("manufacturer"):
                        continue
                    rec.update({"source": "pdf", "source_doc": doc_id, "alert_month": alert_month,
                                "reporting_source": "CDSCO lab" if kind == "central" else "State lab"})
                    rows.append(rec)
    return rows


def parse_all(months_before: str = "2019-01") -> pd.DataFrame:
    idx = pd.read_csv(C.RAW_INDEX)
    idx = idx[(idx.kind.isin(["central", "state"])) & idx.alert_month.notna() & (idx.alert_month < months_before)]
    out = []
    for r in idx.itertuples():
        p = C.RAW_PDFS / f"{r.doc_id}.pdf"
        if p.exists():
            try:
                got = parse_pdf(p, str(r.doc_id), r.alert_month, r.kind)
            except Exception as e:  # a broken PDF should not stop the pipeline
                print(f"  skip {p.name}: {e}")
                got = []
            print(f"  {r.alert_month} {r.kind}: {len(got)} rows from {p.name}")
            out += got
    return pd.DataFrame(out)
