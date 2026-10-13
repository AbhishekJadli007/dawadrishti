"""The ERP's operational database (SQLite): an OLTP schema for public medicine procurement and quality control.

Every business operation goes through erp/service.py, which writes the transaction AND an event to event_log.
The event log is what process mining reads; the data warehouse is loaded from these tables by an ETL step.
"""
from __future__ import annotations

import sqlite3

from .. import config as C

DDL = """
CREATE TABLE IF NOT EXISTS buyer (
  buyer_id TEXT PRIMARY KEY, name TEXT, level TEXT, region TEXT, lab_tat_days REAL);
CREATE TABLE IF NOT EXISTS supplier (
  supplier_id TEXT PRIMARY KEY, name TEXT, state TEXT, manufacturer_id TEXT,  -- link to the national master
  debarred_by TEXT, debarred_on TEXT);
CREATE TABLE IF NOT EXISTS item (
  item_id TEXT PRIMARY KEY, generic_name TEXT, dosage_form TEXT, therapeutic_class TEXT, unit_price REAL);
CREATE TABLE IF NOT EXISTS purchase_order (
  po_id TEXT PRIMARY KEY, buyer_id TEXT, supplier_id TEXT, item_id TEXT, qty INTEGER, po_date TEXT,
  risk_warning TEXT, status TEXT);
CREATE TABLE IF NOT EXISTS batch (
  batch_id TEXT PRIMARY KEY, po_id TEXT, buyer_id TEXT, supplier_id TEXT, item_id TEXT, batch_no TEXT,
  qty INTEGER, mfg_date TEXT, exp_date TEXT, received_at TEXT, warehouse TEXT, qc_status TEXT,
  risk_score REAL, sim_true_quality TEXT);  -- sim_true_quality exists only in the simulator, never shown as fact
CREATE TABLE IF NOT EXISTS qc_sample (
  sample_id TEXT PRIMARY KEY, batch_id TEXT, lab TEXT, sample_code TEXT, drawn_at TEXT, sent_at TEXT,
  reported_at TEXT, result TEXT, decided_at TEXT);
CREATE TABLE IF NOT EXISTS issue (
  issue_id TEXT PRIMARY KEY, batch_id TEXT, facility TEXT, qty INTEGER, issued_at TEXT);
CREATE TABLE IF NOT EXISTS recall (
  recall_id TEXT PRIMARY KEY, batch_id TEXT, started_at TEXT, closed_at TEXT);
CREATE TABLE IF NOT EXISTS payment (
  payment_id TEXT PRIMARY KEY, batch_id TEXT, amount REAL, paid_at TEXT);
CREATE TABLE IF NOT EXISTS event_log (
  event_id INTEGER PRIMARY KEY AUTOINCREMENT, buyer_id TEXT, case_id TEXT, activity TEXT, ts TEXT,
  resource TEXT, supplier_id TEXT, item_id TEXT, erp_module TEXT);
CREATE INDEX IF NOT EXISTS ix_event_case ON event_log(case_id, ts);
CREATE INDEX IF NOT EXISTS ix_batch_buyer ON batch(buyer_id, qc_status);
"""

ACTIVITY_MODULE = {
    "PO created": "Procurement", "PO approved": "Procurement", "Goods received": "Inventory",
    "Quarantined": "Inventory", "Sample drawn": "Quality control", "Sample coded": "Quality control",
    "Sent to lab": "Quality control", "Report received": "Quality control", "Cleared": "Quality control",
    "Held": "Quality control", "Supplier notified": "Vendor management", "Issued": "Inventory",
    "Recall started": "Recall", "Recall closed": "Recall", "Payment released": "Finance",
    "Supplier debarred": "Vendor management",
}


def connect(path=None) -> sqlite3.Connection:
    path = path or C.ERP_DB
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.executescript(DDL)
    return con


def reset(path=None) -> sqlite3.Connection:
    path = path or C.ERP_DB
    if path.exists():
        path.unlink()
    return connect(path)
