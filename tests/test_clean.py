from dawadrishti.etl import clean


def test_split_manufacturer_separates_name_and_address():
    name, addr = clean.split_manufacturer("M/s. Tanpal Pharmaceuticals D-12-13, Focal Point, Nabha- 147201, Punjab")
    assert name == "Tanpal Pharmaceuticals"
    assert "Nabha" in addr
    name, _ = clean.split_manufacturer("M/s. Chem Pharmaceuticals Pvt. Ltd., plot No. 22, Sector-3, SIDCUL")
    assert name.startswith("Chem Pharmaceuticals Pvt. Ltd")


def test_state_from_place_name_then_pin():
    assert clean.state_of("Plot 5, Baddi, Distt. Solan")[0] == "Himachal Pradesh"
    assert clean.state_of("R.B. Road, Pin: 823001")[0] == "Bihar"
    assert clean.state_of("Rangpo East Sikkim-737132")[0] == "Sikkim"
    assert clean.state_of("Shandong Province, China")[0] == "Outside India"


def test_failure_severity():
    assert clean.classify_failure("Particulate matter, Sterility and Assay")["severity"] == "critical"
    assert clean.classify_failure("Dissolution (Buffer Stage)")["primary_failure"] == "Dissolution"
    assert clean.classify_failure("Description")["severity"] == "minor"
    assert clean.classify_failure("Diethylene glycol content")["primary_failure"] == "DEG/EG contamination"


def test_name_key_merges_spelling_variants():
    assert clean.name_key("ABC Pharmaceuticals Pvt. Ltd.") == clean.name_key("M/s ABC Pharma Limited")
    # each pair below was a missed merge found in the labelled entity-resolution pairs
    for a, b in [("Himalaya Meditek Private Ltd", "Himalaya Meditek Pvt.Ltd"), ("Salud Care (I) Pvt.Ltd", "Salud Care (India) Ltd"),
                 ("Cadila Pharmaceticals Ltd", "Cadila Pharmaceuticals Limited"),
                 ("Martin & Brown Bio-sciences K. No", "Martin And Brown Bio-Sciences Pvt. Ltd"),
                 ("Mfg By: AAGYA BIOTECH PVT..LTD", "Aagya Biotech Pvt. Ltd")]:
        assert clean.name_key(a) == clean.name_key(b), (a, b)
    assert clean.compact(clean.name_key("NitinLifesciences Ltd")) == clean.compact(clean.name_key("Nitin Life Sciences Ltd"))


def test_entity_resolution_keeps_states_apart_for_units_but_joins_firms():
    import pandas as pd
    from dawadrishti.etl import entities
    names = pd.Series(["Lupin Ltd", "Lupin Limited", "Lupin Ltd", "Medizest Pharma", "Medisky Pharmaceuticals"])
    states = pd.Series(["Gujarat", "Gujarat", "Maharashtra", "Goa", "Gujarat"])
    keys, _ = entities.resolve(names, states)
    lupin = keys[keys.key == "lupin"]
    assert lupin.unit.nunique() == 2 and lupin.firm.nunique() == 1
    assert keys.firm.nunique() == 3


def test_product_cleaning():
    p = clean.clean_product("PQUIN-2.5 (Primaquine Phosphate Tablets IP 2.5 mg)")
    assert p["generic_name"].startswith("Primaquine") and p["dosage_form"] == "Tablet"
    assert p["therapeutic_class"] == "Antimalarial / antiparasitic"
