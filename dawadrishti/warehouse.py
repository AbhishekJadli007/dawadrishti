"""Step 3 of the ETL: load the national data warehouse (DuckDB star schema) from staging + the ERP database.

  FACT_NSQ_FINDING  one row per failed batch in national alerts (real)        -> supplier, product, failure, lab, date
  FACT_BATCH_EVENT  one row per ERP event (process-mining event log)         -> buyer, supplier, product, activity, date
Both facts share DIM_SUPPLIER, DIM_PRODUCT and DIM_DATE, so one query joins a manufacturer's national record
with how every buyer has bought from it.
"""
from __future__ import annotations

import hashlib
import sqlite3

import duckdb
import pandas as pd

from . import config as C


def _key(*parts) -> str:
    return hashlib.md5("|".join(str(p) for p in parts).encode()).hexdigest()[:12]


def build(db_path=C.WAREHOUSE_DB) -> dict:
    nsq = pd.read_csv(C.STAGING / "nsq_findings.csv")
    erp = sqlite3.connect(C.ERP_DB)
    ev = pd.read_sql("select * from event_log", erp)
    sup = pd.read_sql("select * from supplier", erp)
    items = pd.read_sql("select * from item", erp)
    buyers = pd.read_sql("select * from buyer", erp)
    batches = pd.read_sql("select batch_id, buyer_id, supplier_id, item_id, received_at, qc_status, risk_score from batch", erp)
    erp.close()

    # ---- DIM_SUPPLIER: national manufacturers + ERP suppliers that have no national record
    nat = nsq[nsq.manufacturer_id != "M_UNKNOWN"].groupby(["manufacturer_id"]).agg(
        canonical_name=("manufacturer_canonical", "first"), state=("state", "first"),
        firm_id=("firm_id", "first"), firm_name=("firm_canonical", "first"),
        national_findings=("finding_id", "count"), first_alert=("alert_month", "min"), last_alert=("alert_month", "max"),
        critical_findings=("severity", lambda s: int((s == "critical").sum()))).reset_index()
    nat["supplier_key"] = nat.manufacturer_id
    extra = sup[sup.manufacturer_id.isna()].rename(columns={"name": "canonical_name"})
    extra = extra.assign(supplier_key=extra.supplier_id, manufacturer_id=None, firm_id=None, firm_name=extra.canonical_name,
                         national_findings=0, first_alert=None,
                         last_alert=None, critical_findings=0)[nat.columns]
    dim_supplier = pd.concat([nat, extra], ignore_index=True)
    sup["supplier_key"] = sup.manufacturer_id.fillna(sup.supplier_id)
    dim_supplier = dim_supplier.merge(sup[["supplier_key", "supplier_id", "debarred_by", "debarred_on"]], on="supplier_key", how="left")

    # ---- DIM_PRODUCT
    p1 = nsq[["generic_name", "dosage_form", "therapeutic_class"]]
    p2 = items[["generic_name", "dosage_form", "therapeutic_class"]]
    dim_product = pd.concat([p1, p2]).drop_duplicates(["generic_name", "dosage_form"]).reset_index(drop=True)
    dim_product.insert(0, "product_key", [_key(a, b) for a, b in zip(dim_product.generic_name, dim_product.dosage_form)])

    # ---- DIM_FAILURE, DIM_LAB, DIM_BUYER, DIM_ACTIVITY, DIM_DATE
    dim_failure = nsq[["primary_failure", "severity"]].drop_duplicates().reset_index(drop=True)
    dim_failure.insert(0, "failure_key", [_key(a, b) for a, b in zip(dim_failure.primary_failure, dim_failure.severity)])
    dim_lab = nsq[["reporting_lab", "reporting_source"]].drop_duplicates().reset_index(drop=True)
    dim_lab.insert(0, "lab_key", [_key(a, b) for a, b in zip(dim_lab.reporting_lab, dim_lab.reporting_source)])
    dim_buyer = buyers.rename(columns={"buyer_id": "buyer_key"})
    from .erp.schema import ACTIVITY_MODULE
    dim_activity = pd.DataFrame({"activity": list(ACTIVITY_MODULE), "erp_module": list(ACTIVITY_MODULE.values())})
    dim_activity.insert(0, "activity_key", range(1, len(dim_activity) + 1))
    days = pd.date_range("2017-01-01", "2026-12-31", freq="D")
    dim_date = pd.DataFrame({"date_key": days.strftime("%Y%m%d").astype(int), "day": days.date, "month": days.strftime("%Y-%m"),
                             "quarter": days.year.astype(str) + "-Q" + days.quarter.astype(str), "year": days.year})

    # ---- FACT_NSQ_FINDING
    f = nsq.copy()
    f["supplier_key"] = f.manufacturer_id.where(f.manufacturer_id != "M_UNKNOWN", None)
    f["product_key"] = [_key(a, b) for a, b in zip(f.generic_name, f.dosage_form)]
    f["failure_key"] = [_key(a, b) for a, b in zip(f.primary_failure, f.severity)]
    f["lab_key"] = [_key(a, b) for a, b in zip(f.reporting_lab, f.reporting_source)]
    f["date_key"] = (f.alert_month.str.replace("-", "") + "01").astype(int)
    fact_nsq = f[["finding_id", "supplier_key", "product_key", "failure_key", "lab_key", "date_key", "batch_no", "is_spurious",
                  "failure_categories", "state", "product_name", "manufacturer", "nsq_result", "source", "source_doc"]].rename(
        columns={"product_name": "product_name_raw", "manufacturer": "manufacturer_raw", "nsq_result": "nsq_result_raw"})

    # ---- FACT_BATCH_EVENT
    e = ev.merge(sup[["supplier_id", "supplier_key"]], on="supplier_id", how="left")
    e = e.merge(items.assign(product_key=[_key(a, b) for a, b in zip(items.generic_name, items.dosage_form)])[["item_id", "product_key"]],
                on="item_id", how="left")
    e = e.merge(dim_activity[["activity", "activity_key"]], on="activity", how="left")
    e["ts"] = pd.to_datetime(e.ts, format="ISO8601")
    e["date_key"] = e.ts.dt.strftime("%Y%m%d").astype(int)
    fact_event = e[["event_id", "buyer_id", "case_id", "activity_key", "supplier_key", "product_key", "date_key", "ts", "resource"]].rename(
        columns={"buyer_id": "buyer_key"})

    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    con = duckdb.connect(str(db_path))
    for name, df in [("dim_supplier", dim_supplier), ("dim_product", dim_product), ("dim_failure", dim_failure),
                     ("dim_lab", dim_lab), ("dim_buyer", dim_buyer), ("dim_activity", dim_activity), ("dim_date", dim_date),
                     ("fact_nsq_finding", fact_nsq), ("fact_batch_event", fact_event), ("erp_batch", batches)]:
        con.register("tmp_df", df)
        con.execute(f"CREATE TABLE {name} AS SELECT * FROM tmp_df")
        con.unregister("tmp_df")
    con.execute("""
      CREATE VIEW v_findings AS
      SELECT f.finding_id, d.month, d.year, f.state, s.canonical_name AS manufacturer, s.supplier_key AS manufacturer_id,
             s.firm_id, s.firm_name,
             p.generic_name, p.dosage_form, p.therapeutic_class, x.primary_failure, x.severity,
             l.reporting_lab, l.reporting_source, f.is_spurious, f.batch_no
      FROM fact_nsq_finding f
      LEFT JOIN dim_supplier s ON f.supplier_key = s.supplier_key
      JOIN dim_product p ON f.product_key = p.product_key
      JOIN dim_failure x ON f.failure_key = x.failure_key
      JOIN dim_lab l ON f.lab_key = l.lab_key
      JOIN dim_date d ON f.date_key = d.date_key""")
    con.execute("""
      CREATE VIEW v_events AS
      SELECT e.event_id, e.case_id, b.name AS buyer, e.buyer_key AS buyer_id, a.activity, a.erp_module, e.ts,
             e.resource, s.canonical_name AS supplier, e.supplier_key, p.generic_name, p.dosage_form
      FROM fact_batch_event e
      JOIN dim_buyer b ON e.buyer_key = b.buyer_key
      JOIN dim_activity a ON e.activity_key = a.activity_key
      LEFT JOIN dim_supplier s ON e.supplier_key = s.supplier_key
      LEFT JOIN dim_product p ON e.product_key = p.product_key""")
    counts = {t: con.execute(f"select count(*) from {t}").fetchone()[0] for t in
              ["dim_supplier", "dim_product", "dim_failure", "dim_lab", "dim_buyer", "dim_activity", "dim_date",
               "fact_nsq_finding", "fact_batch_event"]}
    con.close()
    return counts


def main():
    counts = build()
    print("warehouse built:", counts)


if __name__ == "__main__":
    main()
