"""The naming policy and the memory's checks, as tests: what the public can see, and what a buyer's ERP gets."""
import shutil
import sqlite3
import types

import duckdb
import pytest
from fastapi.testclient import TestClient

from dawadrishti import config as C


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db = tmp_path / "erp.sqlite"
    shutil.copy(C.ERP_DB, db)
    monkeypatch.setattr(C, "ERP_DB", db)
    from api.main import app
    return TestClient(app)


def test_public_risk_endpoint_withholds_the_ranked_list(client):
    pub = client.get("/api/risk").json()
    assert "inspect_next" not in pub["factory"] and pub["factory"]["test"]["results"]
    assert client.get("/api/manufacturer/M00008").status_code in (404, 405) or "risk_rank" not in client.get("/api/manufacturer/M00008").text


def test_buyer_view_needs_the_key_when_one_is_configured(client, monkeypatch):
    import api.main as A
    monkeypatch.setattr(A, "BUYER_KEY", "secret")
    q = "/api/v1/lookup?q=Nestor%20Pharmaceuticals%20Ltd&view=buyer"
    assert client.get(q).status_code == 403
    assert client.get("/api/risk?view=buyer").status_code == 403
    ok = client.get(q, headers={"X-Buyer-Key": "secret"})
    assert ok.status_code == 200 and ok.json()["buyer"]["graded_response"]
    assert client.get("/api/v1/lookup?q=Nestor%20Pharmaceuticals%20Ltd&view=public").status_code == 200


def test_a_received_batch_already_on_the_national_list_is_held(client):
    from dawadrishti.memory import same_product
    con = sqlite3.connect(C.ERP_DB)
    con.row_factory = sqlite3.Row
    rows = con.execute("""select distinct p.buyer_id, p.item_id, i.generic_name, s.supplier_id, s.manufacturer_id
                          from purchase_order p join supplier s using(supplier_id) join item i using(item_id)
                          where s.manufacturer_id is not null""").fetchall()
    con.close()
    w = duckdb.connect(str(C.WAREHOUSE_DB), read_only=True)
    pick = None
    for r in rows:
        for bn, g in w.execute("select batch_no, generic_name from v_findings where manufacturer_id = ? and length(batch_no) > 3",
                               [r["manufacturer_id"]]).fetchall():
            if same_product(g, r["generic_name"]):
                pick = (r, bn)
                break
        if pick:
            break
    w.close()
    r, bn = pick
    po = client.post("/api/erp/po", json={"buyer_id": r["buyer_id"], "item_id": r["item_id"], "supplier_id": r["supplier_id"],
                                          "qty": 100, "override": True}).json()
    got = client.post("/api/erp/receive", json={"case_id": po["case_id"], "batch_no": bn.lower()}).json()
    assert got["status"] == "held" and got["national_alert_on_this_batch"]
    assert client.post("/api/erp/issue", json={"case_id": po["case_id"]}).json()["issued"] is False
    # the same batch number on a different product is not the same batch
    po2 = client.post("/api/erp/po", json={"buyer_id": r["buyer_id"], "item_id": r["item_id"], "supplier_id": r["supplier_id"],
                                           "qty": 100, "override": True}).json()
    assert client.post("/api/erp/receive", json={"case_id": po2["case_id"], "batch_no": "NOT-A-REAL-BATCH-1"}).json()["status"] == "quarantine"


def test_llm_only_chooses_a_template_and_bad_choices_are_rejected(monkeypatch):
    from dawadrishti.ai import ask as A
    replies = iter(['{"template": "top_units", "params": {"state": "gujarat", "since": "2024"}}',
                    '{"template": "top_units", "params": {"state": "Gujarat\'; drop table v_findings; --"}}',
                    'SELECT * FROM v_findings'])

    class FakeClient:
        def __init__(self, api_key):
            self.models = types.SimpleNamespace(generate_content=lambda model, contents: types.SimpleNamespace(text=next(replies)))
    monkeypatch.setattr(C, "GEMINI_KEY", "test")
    monkeypatch.setattr("google.genai.Client", FakeClient)
    r = A.ask("Which Gujarat factories failed most since 2024?")
    assert r["template"] == "top_units" and r["params"]["state"] == "Gujarat" and r["rows"]
    with pytest.raises(ValueError):
        A.ask("anything")                       # parameter not in the data
    with pytest.raises(ValueError):
        A.ask("anything else")                  # model tried to answer with SQL: no template chosen


def test_reviewer_decisions_override_the_matcher():
    import pandas as pd
    from dawadrishti.etl import clean, entities
    names = pd.Series(["Om Biomedic Pvt Ltd", "Om Biometic Pvt Ltd", "Medizest Pharma", "Medibest Pharma"])
    states = pd.Series(["Uttarakhand", "Uttarakhand", "Goa", "Gujarat"])
    base, _ = entities.resolve(names, states, decisions=(set(), set()))
    k = {n: clean.name_key(n) for n in names}
    must = {frozenset((k["Om Biomedic Pvt Ltd"], k["Om Biometic Pvt Ltd"]))}
    cannot = {frozenset((k["Medizest Pharma"], k["Medibest Pharma"]))}
    got, _ = entities.resolve(names, states, decisions=(must, cannot))
    by = got.set_index("key")
    assert by.loc[k["Om Biomedic Pvt Ltd"], "unit"] == by.loc[k["Om Biometic Pvt Ltd"], "unit"]
    assert by.loc[k["Medizest Pharma"], "firm"] != by.loc[k["Medibest Pharma"], "firm"]


def test_exact_batch_needs_the_same_product():
    from dawadrishti.memory import same_product as sp
    assert sp("Paracetamol", "Paracetamol Tablets IP 500 mg") and sp("Amoxicillin", "Amoxycillin")
    assert sp("Calcium And Vitamin D3", "Calcium Carbonate and Vitamin D3")
    assert not sp("Bupropion Hydrochloride", "Metochlopramide Hydrochloride")   # shared salt name only
    assert not sp("Nitrazepam", "Lorazepam") and not sp("Vitamin D3", "Vitamin K") and not sp("Sodium Valproate", "Sodium Chloride")
