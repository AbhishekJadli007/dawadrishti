from dawadrishti.mining import conformance as K

XES = """<?xml version="1.0" encoding="UTF-8"?>
<log xmlns="http://www.xes-standard.org/">
 <trace><string key="concept:name" value="c1"/><string key="Item Category" value="3-way match, invoice after GR"/>
  <event><string key="concept:name" value="Create Purchase Order Item"/><date key="time:timestamp" value="2018-01-01T10:00:00.000+01:00"/></event>
  <event><string key="concept:name" value="Record Invoice Receipt"/><date key="time:timestamp" value="2018-01-03T10:00:00.000+01:00"/></event>
  <event><string key="concept:name" value="Clear Invoice"/><date key="time:timestamp" value="2018-01-04T10:00:00.000+01:00"/></event>
  <event><string key="concept:name" value="Record Goods Receipt"/><date key="time:timestamp" value="2018-01-05T10:00:00.000+01:00"/></event>
 </trace>
 <trace><string key="concept:name" value="c2"/><string key="Item Category" value="3-way match, invoice after GR"/>
  <event><string key="concept:name" value="Create Purchase Order Item"/><date key="time:timestamp" value="2018-01-01T10:00:00.000+01:00"/></event>
  <event><string key="concept:name" value="Record Goods Receipt"/><date key="time:timestamp" value="2018-01-02T10:00:00.000+01:00"/></event>
  <event><string key="concept:name" value="Record Invoice Receipt"/><date key="time:timestamp" value="2018-01-03T10:00:00.000+01:00"/></event>
  <event><string key="concept:name" value="Clear Invoice"/><date key="time:timestamp" value="2018-01-04T10:00:00.000+01:00"/></event>
 </trace>
</log>"""


def test_bpi_reader_and_rules(tmp_path):
    p = tmp_path / "mini.xes"
    p.write_text(XES)
    log, attrs = K.load_bpi(str(p))
    assert set(log.case_id) == {"c1", "c2"} and len(log) == 8
    v = K.check(log, K.BPI_RULES, attrs)
    assert set(v[v.case_id == "c1"].rule) == {"P1", "P2"} and v[v.case_id == "c2"].empty


def test_declarative_engine_matches_hand_written_rules():
    x = K.crosscheck()
    assert x["agree"], x["rules"]
