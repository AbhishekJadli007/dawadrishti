"""DawaDrishti HTTP API (FastAPI). Serves the ERP operations, the analytics and the built web app.

    uvicorn api.main:app --port 8000
"""
from __future__ import annotations

import json
from functools import lru_cache

import duckdb
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from dawadrishti import config as C
from dawadrishti import memory as M
from dawadrishti.ai import ask as AI
from dawadrishti.erp import service as S
from dawadrishti.erp.schema import connect

app = FastAPI(title="DawaDrishti API", version="2.0.0",
              description="A national memory of medicine-quality failures, with a lookup that any buyer's ERP can call. "
                          "Public responses show the published record only; predicted scores appear only in the buyer view.")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
WEB = C.ROOT / "web" / "dist"


@lru_cache(maxsize=8)
def artifact(name: str) -> dict:
    p = C.ARTIFACTS / f"{name}.json"
    if not p.exists():
        raise HTTPException(503, f"Run `python -m dawadrishti build` first ({name}.json missing)")
    return json.loads(p.read_text())


def wh():
    return duckdb.connect(str(C.WAREHOUSE_DB), read_only=True)


def _guard(fn):
    try:
        return fn()
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


# ------------------------------------------------------------------ analytics
@app.get("/api/health")
def health():
    return {"ok": True, "gemini": bool(C.GEMINI_KEY)}


@app.get("/api/overview")
def overview():
    dm, pm, rk, net = artifact("data_mining"), artifact("process_mining"), artifact("risk"), artifact("network_effect")
    con = wh()
    k = con.execute("""select count(*) n, count(distinct manufacturer_id) m, count(distinct state) s,
                              sum(case when severity='critical' then 1 else 0 end) c, min(month), max(month),
                              sum(case when is_spurious then 1 else 0 end) sp from v_findings""").fetchone()
    con.close()
    return {"kpis": {"findings": k[0], "manufacturers": k[1], "states": k[2], "critical": k[3], "since": k[4], "as_of": k[5],
                     "spurious": k[6], "repeat_share": dm["repeat"]["repeat_share_of_findings"],
                     "recurrence_12m": dm["repeat"]["recurrence_12m"]},
            "geography": dm["geography"], "monthly": dm["trends"]["monthly"], "anomalies": dm["anomalies"][:8],
            "benchmark": pm["benchmark"], "network": net, "risk_test": rk["factory"]["test"],
            "batch_test": rk["batch"]["test"]}


@app.get("/api/study")
def study():
    """The headline study on real data: how much of India's failed-drug record comes from firms already on it."""
    return artifact("memory_study")


@app.get("/api/quality")
def data_quality(queue: int = 60):
    """How far the data can be trusted: PDF extraction audit and entity-resolution evaluation with its review queue."""
    er = dict(artifact("entity_resolution"))
    er["review_queue_total"] = len(er["review_queue"])
    er["review_queue"] = er["review_queue"][:queue]
    return {"extraction": artifact("extraction_audit"), "entities": er}


@app.get("/api/v1/lookup")
def lookup(q: str, view: str = "public", state: str | None = None, molecule: str | None = None):
    """The memory's lookup, for an ERP or a person: a manufacturer name (as written on an invoice) or id.
    view=public returns the published record only; view=buyer adds the graded response, model score and alternatives."""
    if view not in ("public", "buyer"):
        raise HTTPException(400, "view must be public or buyer")
    if len(q.strip()) < 2:
        raise HTTPException(400, "query too short")
    return M.lookup(q.strip(), view=view, state=state, molecule=molecule)


@app.get("/api/mining")
def mining():
    return artifact("data_mining")


@app.get("/api/process")
def process(buyer: str | None = None):
    pm = artifact("process_mining")
    out = {k: v for k, v in pm.items() if k != "discovery_by_buyer"}
    if buyer:
        if buyer not in pm["discovery_by_buyer"]:
            raise HTTPException(400, "unknown buyer")
        out["discovery"] = pm["discovery_by_buyer"][buyer]
    return out


@app.get("/api/violations")
def violations(rule: str | None = None, buyer: str | None = None, limit: int = 200):
    v = pd.read_csv(C.ARTIFACTS / "violations.csv")
    if rule:
        v = v[v.rule == rule]
    if buyer:
        v = v[v.buyer_id == buyer]
    return {"total": int(len(v)), "rows": v.head(limit).fillna("").to_dict(orient="records")}


@app.get("/api/risk")
def risk():
    return artifact("risk")


@app.get("/api/search")
def search(q: str, limit: int = 12):
    if len(q.strip()) < 2:
        return []
    con = wh()
    rows = con.execute("""select supplier_key, canonical_name, state, national_findings, critical_findings from dim_supplier
                          where canonical_name ilike ? order by national_findings desc limit ?""", [f"%{q.strip()}%", limit]).df()
    con.close()
    return rows.to_dict(orient="records")


@app.get("/api/manufacturer/{mid}")
def manufacturer(mid: str):
    con = wh()
    s = con.execute("select * from dim_supplier where supplier_key = ?", [mid]).df()
    if s.empty:
        con.close()
        raise HTTPException(404, "unknown manufacturer")
    f = con.execute("""select month, generic_name, dosage_form, therapeutic_class, primary_failure, severity, reporting_lab,
                              reporting_source, batch_no, is_spurious from v_findings where manufacturer_id = ? order by month desc""", [mid]).df()
    buys = con.execute("""select buyer, count(distinct case_id) orders, min(ts) as first_order, max(ts) as last_order from v_events
                          where supplier_key = ? and activity = 'PO created' group by 1 order by orders desc""", [mid]).df()
    con.close()
    rank = next((r for r in artifact("risk")["factory"]["inspect_next"] if r["manufacturer_id"] == mid), None)
    return {"profile": s.iloc[0].where(s.iloc[0].notna(), None).to_dict(), "findings": f.to_dict(orient="records"),
            "by_month": f.groupby("month").size().reset_index(name="n").to_dict(orient="records"),
            "by_failure": f.primary_failure.value_counts().to_dict(), "buyers": buys.astype(str).to_dict(orient="records"),
            "risk_rank": rank}


# ------------------------------------------------------------------ ERP
class POIn(BaseModel):
    buyer_id: str
    item_id: str
    supplier_id: str
    qty: int = Field(5000, ge=1, le=10_000_000)
    override: bool = False


class ReceiveIn(BaseModel):
    case_id: str
    batch_no: str = "BN-NEW"
    mfg_date: str = "2026-09-01"
    exp_date: str = "2028-08-31"


class ResultIn(BaseModel):
    case_id: str
    passed: bool
    failure: str = ""


class IssueIn(BaseModel):
    case_id: str
    facility: str = "District hospital 1"
    qty: int = 1000


@app.get("/api/erp/masters")
def masters():
    con = connect()
    buyers = [dict(r) for r in con.execute("select * from buyer")]
    items = [dict(r) for r in con.execute("select * from item order by (therapeutic_class like 'Other%'), (generic_name like '(%'), generic_name")]
    con.close()
    return {"buyers": buyers, "items": items}


@app.get("/api/erp/suppliers")
def suppliers(buyer_id: str, item_id: str):
    """Suppliers on this buyer's rate contract for the item (from its purchase history), with the national check."""
    con = connect()
    ids = [r[0] for r in con.execute("select distinct supplier_id from purchase_order where buyer_id=? and item_id=?", (buyer_id, item_id))]
    if len(ids) < 3:
        ids += [r[0] for r in con.execute("select distinct supplier_id from purchase_order where item_id=? limit 6", (item_id,)) if r[0] not in ids]
    con.close()
    return [S.national_check(s) for s in ids[:6]]


@app.get("/api/erp/contract")
def contract(buyer_id: str, item_id: str):
    """Concentration of the buyer's supply for this item and days of cover (simulated ERP)."""
    return S.contract_status(buyer_id, item_id)


@app.get("/api/erp/check/{supplier_id}")
def check(supplier_id: str):
    return _guard(lambda: S.national_check(supplier_id))


@app.post("/api/erp/po")
def po(body: POIn):
    return _guard(lambda: S.create_po(body.buyer_id, body.item_id, body.supplier_id, body.qty, body.override))


@app.post("/api/erp/receive")
def receive(body: ReceiveIn):
    return _guard(lambda: S.receive(body.case_id, body.batch_no, body.mfg_date, body.exp_date))


@app.post("/api/erp/result")
def result(body: ResultIn):
    return _guard(lambda: S.record_result(body.case_id, body.passed, body.failure))


@app.post("/api/erp/issue")
def issue(body: IssueIn):
    return _guard(lambda: S.issue(body.case_id, body.facility, body.qty))


@app.get("/api/erp/queue")
def erp_queue(buyer_id: str):
    return S.queue(buyer_id)


@app.get("/api/erp/case/{case_id}")
def erp_case(case_id: str):
    return S.case_timeline(case_id)


@app.get("/api/erp/history")
def erp_history(buyer_id: str, limit: int = 60):
    con = connect()
    rows = [dict(r) for r in con.execute("""select b.batch_id, b.qc_status, b.risk_score, b.received_at, s.name supplier,
                                                   i.generic_name, i.dosage_form from batch b join supplier s using(supplier_id)
                                                   join item i using(item_id) where b.buyer_id=? and b.batch_id not like '%-L%'
                                                   order by b.received_at desc limit ?""", (buyer_id, limit))]
    con.close()
    return rows


# ------------------------------------------------------------------ AI
class AskIn(BaseModel):
    question: str = Field(..., min_length=3, max_length=500)


@app.get("/api/ask/presets")
def presets():
    return {"questions": list(AI.PRESETS), "gemini": bool(C.GEMINI_KEY)}


@app.post("/api/ask")
def ask(body: AskIn):
    try:
        return AI.ask(body.question)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except Exception as e:  # LLM or SQL error: say so plainly
        raise HTTPException(502, f"Could not answer: {e}") from e


# ------------------------------------------------------------------ web app
if WEB.exists():
    app.mount("/assets", StaticFiles(directory=WEB / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        f = WEB / path
        return FileResponse(f if path and f.is_file() else WEB / "index.html")
