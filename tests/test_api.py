import shutil

import pytest
from fastapi.testclient import TestClient

from dawadrishti import config as C


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db = tmp_path / "erp.sqlite"
    shutil.copy(C.ERP_DB, db)
    monkeypatch.setattr(C, "ERP_DB", db)   # never touch the real ERP database
    from api.main import app
    return TestClient(app)


def test_health_and_overview(client):
    assert client.get("/api/health").json()["ok"]
    o = client.get("/api/overview").json()
    assert o["kpis"]["findings"] > 6000 and o["kpis"]["manufacturers"] > 1500


def test_curated_question(client):
    q = client.get("/api/ask/presets").json()["questions"][0]
    r = client.post("/api/ask", json={"question": q}).json()
    assert r["rows"] and "select" in r["sql"].lower()


def test_questions_only_run_templates_with_checked_parameters(client):
    from dawadrishti.ai import ask as A
    with pytest.raises(ValueError):
        A.run("top_units", {"state": "Atlantis"})                 # not a value in the data
    with pytest.raises(ValueError):
        A.run("top_units", {"state": "Gujarat'; drop table v_findings; --"})
    with pytest.raises(ValueError):
        A.run("anything goes", {})
    t, p = A.parse_rules("Which antibiotic tablets from Gujarat failed since 2024?")
    assert t == "top_units" and p["state"] == "Gujarat" and p["since"] == "2024"


def test_lookup_public_view_has_no_score_and_uncertain_names_get_candidates(client):
    r = client.get("/api/v1/lookup?q=Nestor%20Pharmaceuticals%20Ltd&view=public").json()
    assert r["record"]["alerts"] > 0 and "buyer" not in r and r["data_does_not_contain"]
    assert "probability" not in str(r)
    b = client.get("/api/v1/lookup?q=Nestor%20Pharmaceuticals%20Ltd&view=buyer").json()
    assert b["buyer"]["graded_response"]["level"] in (0, 1, 2, 3)
    u = client.get("/api/v1/lookup?q=Sresan%20Pharmaceuticals&view=public").json()
    assert u["record"] is None and u["identity"]["candidates"]


def test_erp_flow_blocks_release_until_clearance(client):
    m = client.get("/api/erp/masters").json()
    buyer, item = m["buyers"][0]["buyer_id"], m["items"][0]["item_id"]
    sups = client.get(f"/api/erp/suppliers?buyer_id={buyer}&item_id={item}").json()
    s = next((x for x in sups if x["level"] != "block"), sups[0])
    po = client.post("/api/erp/po", json={"buyer_id": buyer, "item_id": item, "supplier_id": s["supplier_id"], "qty": 100, "override": True}).json()
    case = po["case_id"]
    assert client.post("/api/erp/receive", json={"case_id": case}).json()["status"] == "quarantine"
    blocked = client.post("/api/erp/issue", json={"case_id": case}).json()
    assert blocked["issued"] is False and blocked["rule"] == "R1"
    assert client.post("/api/erp/result", json={"case_id": case, "passed": True}).json()["status"] == "cleared"
    assert client.post("/api/erp/issue", json={"case_id": case}).json()["issued"] is True
    events = [e["activity"] for e in client.get(f"/api/erp/case/{case}").json()["events"]]
    assert events.index("Cleared") < events.index("Issued")
