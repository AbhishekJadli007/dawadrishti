"""Step 1 of the ETL: find and download CDSCO's monthly NSQ / spurious drug alert PDFs.

CDSCO lists alerts on two notice pages. Each row links to a download endpoint whose id is a base64 number;
the endpoint returns either the PDF itself or a small HTML page with an <iframe> pointing at the PDF.
Files are cached in data/raw/pdfs/, so the crawl is polite and only runs once.
"""
from __future__ import annotations

import base64
import html
import re
import time

import pandas as pd
import requests

from .. import config as C

ROW = re.compile(r"<tr>\s*<td>\d+</td>\s*<td>(.*?)</td>\s*<td>([\d\-A-Za-z]+)</td>\s*<td><a href='([^']+)'", re.S)
MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}


def classify(title: str) -> str | None:
    t = title.lower()
    if "month" not in t:
        return None
    if "spurious" in t and "standard" not in t and "nsq" not in t:
        return "spurious"
    if "state" in t:
        return "state"
    if "nsq" in t or "not of standard" in t or "standard quality" in t:
        return "central"
    return None


def alert_month(title: str) -> str | None:
    m = re.search(r"month(?:\s+of)?\s*[-:]?\s*([A-Za-z]+)[\s\-,'’]*(\d{2,4})", title, re.I)
    if not m:
        return None
    mon = MONTHS.get(m.group(1)[:3].lower())
    yr = int(m.group(2))
    yr = yr + 2000 if yr < 100 else yr
    return f"{yr:04d}-{mon:02d}" if mon else None


def list_alerts(session: requests.Session) -> pd.DataFrame:
    rows = []
    for page in C.ALERT_PAGES:
        h = session.get(page, timeout=60).text
        for title, published, href in ROW.findall(h):
            title = html.unescape(re.sub(r"\s+", " ", title)).strip()
            kind = classify(title)
            nid = re.search(r"num_id=([^&']+)", href)
            if not kind or not nid:
                continue
            doc_id = base64.b64decode(nid.group(1)).decode()
            rows.append({"doc_id": doc_id, "title": title, "published": published, "kind": kind,
                         "alert_month": alert_month(title), "url": C.CDSCO + href})
    df = pd.DataFrame(rows).drop_duplicates("doc_id").sort_values(["alert_month", "kind"]).reset_index(drop=True)
    return df


def download(session: requests.Session, row) -> str:
    path = C.RAW_PDFS / f"{row.doc_id}.pdf"
    if path.exists() and path.stat().st_size > 1000:
        return "cached"
    r = session.get(row.url, timeout=120)
    body = r.content
    if not body.startswith(b"%PDF"):
        frame = re.search(rb"src=['\"]([^'\"]+\.pdf)['\"]", body, re.I)
        if not frame:
            return "no-pdf"
        real = frame.group(1).decode().replace(" ", "%20")
        r = session.get(C.CDSCO + real if real.startswith("/") else real, timeout=120)
        body = r.content
        if not body.startswith(b"%PDF"):
            return "no-pdf"
    path.write_bytes(body)
    time.sleep(0.5)  # be polite to a government server
    return "downloaded"


def main():
    C.RAW_PDFS.mkdir(parents=True, exist_ok=True)
    s = requests.Session()
    s.headers.update(C.UA)
    idx = list_alerts(s)
    print(f"found {len(idx)} monthly alert documents "
          f"({idx.alert_month.min()} to {idx.alert_month.max()}; {idx.kind.value_counts().to_dict()})")
    status = []
    for row in idx.itertuples():
        try:
            status.append(download(s, row))
        except requests.RequestException as e:
            status.append(f"error: {e.__class__.__name__}")
        print(f"  {row.alert_month} {row.kind:8s} {row.doc_id}: {status[-1]}")
    idx["status"] = status
    idx.to_csv(C.RAW_INDEX, index=False)
    print(f"saved index to {C.RAW_INDEX.relative_to(C.ROOT)}")


if __name__ == "__main__":
    main()
