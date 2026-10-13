"""Paths and constants. Every assumption used by the simulator is documented in data/ASSUMPTIONS.md."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RAW_PDFS = DATA / "raw" / "pdfs"
RAW_INDEX = DATA / "raw" / "alerts_index.csv"
STAGING = DATA / "staging"
WAREHOUSE_DB = DATA / "warehouse" / "dawadrishti.duckdb"
ERP_DB = Path(os.environ.get("DAWADRISHTI_ERP_DB", DATA / "erp" / "erp.sqlite"))
ARTIFACTS = ROOT / "artifacts"
LLM_CACHE = DATA / "llm_cache.json"

SEED = 42

CDSCO = "https://cdsco.gov.in"
ALERT_PAGES = [
    CDSCO + "/opencms/opencms/en/Notifications/Alerts/",
    CDSCO + "/opencms/opencms/en/Alerts/",
]
UA = {"User-Agent": "Mozilla/5.0 (DawaDrishti open-source research; contact via GitHub)"}

GEMINI_MODEL = os.environ.get("DAWADRISHTI_GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

# [SOURCE] Lok Sabha answer (via IndiaMedToday, Dec 2025): 1.16 lakh samples tested, 3,104 NSQ in 2024-25.
NATIONAL_NSQ_RATE = 3104 / 116000
