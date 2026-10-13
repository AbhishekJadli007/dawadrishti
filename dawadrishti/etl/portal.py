"""Step 1b of the ETL: download CDSCO's NSQ and spurious-drug records from its public portal (JSON).

Since 2025 CDSCO publishes alerts on cdscoonline.gov.in, whose page loads month-by-month JSON from
public endpoints (the same calls the page itself makes). Each month is cached in data/raw/portal/.
"""
from __future__ import annotations

import json
import time

import requests

from .. import config as C

BASE = "https://cdscoonline.gov.in/CDSCO"
OUT = C.DATA / "raw" / "portal"
TABS = {"nsq": "filteredNsqDrugTable", "spurious": "filteredSpuriousDrugTable"}
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _json(r: requests.Response):
    d = r.json()
    return json.loads(d) if isinstance(d, str) else d


def fetch_month(s: requests.Session, tab: str, year: str, mon: str, force: bool = False) -> int:
    path = OUT / f"{tab}_{year}-{MON.index(mon) + 1:02d}.json"
    if path.exists() and not force:
        return len(json.loads(path.read_text()))
    r = s.get(f"{BASE}/{TABS[tab]}", params={"month": f"{mon}-{year}", "source": "All", "tab": tab}, timeout=120)
    r.raise_for_status()
    rows = _json(r)
    rows = rows.get("aaData", rows) if isinstance(rows, dict) else rows
    path.write_text(json.dumps(rows, ensure_ascii=False))
    time.sleep(0.4)
    return len(rows)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    s = requests.Session()
    s.headers.update(C.UA)
    total = {}
    for tab in TABS:
        years = _json(s.get(f"{BASE}/reportingYears", params={"tab": tab}, timeout=60))
        for y in years:
            months = _json(s.get(f"{BASE}/publicReportingMonths", params={"year": y, "tab": tab}, timeout=60))
            for m in months:
                for attempt in range(3):
                    try:
                        n = fetch_month(s, tab, y, m)
                        break
                    except (requests.RequestException, ValueError) as e:
                        n = f"error {e.__class__.__name__}"
                        time.sleep(2 * (attempt + 1))
                total[f"{tab} {y}-{m}"] = n
                print(f"  {tab:8s} {y}-{m}: {n}")
    ok = sum(v for v in total.values() if isinstance(v, int))
    print(f"done: {ok} records across {len(total)} months")


if __name__ == "__main__":
    main()
