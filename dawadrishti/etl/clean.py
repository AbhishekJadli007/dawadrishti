"""Step 2 of the ETL: turn raw alert records into clean, analysable fields (rule-based, no LLM needed).

  manufacturer text -> company name + address + state (from state names in the address, else the PIN code)
  product text      -> generic name + dosage form + therapeutic class
  NSQ result text   -> failure categories + the most severe one (critical / major / minor)

The optional LLM step (etl/llm.py) refines names afterwards; every original string is kept beside its cleaned value.
"""
from __future__ import annotations

import re

STATES = [
    ("Himachal Pradesh", r"himachal|\bh\.?\s?p\.?\b(?!\s*ltd)|baddi|nalagarh|solan|kala\s?amb|paonta|parwanoo|kangra|una\b"),
    ("Uttarakhand", r"uttarakhand|uttaranchal|\bu\.?k\.?\b|haridwar|roorkee|dehradun|selaqui|sidcul|rudrapur|kashipur|pantnagar|bhagwanpur"),
    ("Jammu & Kashmir", r"jammu|kashmir|\bj\s?&\s?k\b|kathua|samba"),
    ("Punjab", r"punjab|ludhiana|mohali|amritsar|jalandhar|derabassi|dera bassi|nabha|patiala|lalru"),
    ("Haryana", r"haryana|gurgaon|gurugram|faridabad|panchkula|ambala|bahadurgarh|sonipat|karnal|panipat|rohtak|hisar|yamuna\s?nagar|manesar|bawal"),
    ("Chandigarh", r"chandigarh"),
    ("Delhi", r"new delhi|\bdelhi\b"),
    ("Uttar Pradesh", r"uttar pradesh|\bu\.?\s?p\.?\b|ghaziabad|noida|lucknow|kanpur|meerut|agra|saharanpur|varanasi|aligarh|bareilly"),
    ("Rajasthan", r"rajasthan|jaipur|bhiwadi|alwar|udaipur|jodhpur|neemrana|kota\b|sitapura"),
    ("Gujarat", r"gujarat|ahmedabad|vadodara|baroda|surat|rajkot|ankleshwar|vapi|gandhinagar|sanand|bharuch|valsad|kalol|changodar|mehsana"),
    ("Daman, Diu & DNH", r"daman|silvassa|dadra|nagar haveli"),
    ("Maharashtra", r"maharashtra|mumbai|thane|pune|nashik|nasik|aurangabad|nagpur|tarapur|boisar|palghar|bhiwandi|navi mumbai|ambernath|satara|kolhapur|jalgaon"),
    ("Goa", r"\bgoa\b|verna|ponda|madgaon|margao"),
    ("Madhya Pradesh", r"madhya pradesh|\bm\.?\s?p\.?\b|indore|bhopal|pithampur|dewas|gwalior|jabalpur|ujjain|malanpur"),
    ("Chhattisgarh", r"chhattisgarh|chattisgarh|raipur|bilaspur|durg|bhilai"),
    ("Telangana", r"telangana|hyderabad|secunderabad|medak|sangareddy|rangareddy|jeedimetla|bollaram|patancheru"),
    ("Andhra Pradesh", r"andhra pradesh|\ba\.?\s?p\.?\b|visakhapatnam|vizag|vijayawada|guntur|nellore|anakapalli|srikakulam|kakinada"),
    ("Karnataka", r"karnataka|bangalore|bengaluru|mysore|mysuru|hubli|dharwad|belgaum|belagavi|mangalore|tumkur"),
    ("Tamil Nadu", r"tamil\s?nadu|\bt\.?\s?n\.?\b|chennai|madras|coimbatore|madurai|kanch[ei]{1,2}puram|hosur|salem|trichy|tiruchirappalli|chengalpattu|sriperumbudur"),
    ("Puducherry", r"puducherry|pondicherry"),
    ("Kerala", r"kerala|kochi|cochin|ernakulam|thiruvananthapuram|trivandrum|kozhikode|thrissur|palakkad|alappuzha"),
    ("West Bengal", r"west bengal|\bw\.?\s?b\.?\b|kolkata|calcutta|howrah|durgapur|siliguri|hooghly"),
    ("Sikkim", r"sikkim|rangpo|gangtok|majitar"),
    ("Odisha", r"odisha|orissa|bhubaneswar|cuttack"),
    ("Assam", r"assam|guwahati|gauhati"),
    ("Bihar", r"bihar|patna|hajipur|muzaffarpur|gaya\b|bhagalpur"),
    ("Jharkhand", r"jharkhand|ranchi|jamshedpur|dhanbad|bokaro"),
    ("Meghalaya", r"meghalaya|shillong|byrnihat"),
    ("Tripura", r"tripura|agartala"),
]
STATES = [(n, re.compile(p, re.I)) for n, p in STATES]

FOREIGN = re.compile(r"\b(china|p\.?r\.?c\.?|bangladesh|nepal|pakistan|sri lanka|usa|u\.s\.a|united states|germany|italy|"
                     r"spain|france|korea|japan|switzerland|belgium|netherlands|austria|ireland|united kingdom|\buk\b|"
                     r"egypt|vietnam|indonesia|singapore|thailand|turkey|hungary|poland|canada|australia|brazil|argentina|"
                     r"israel|jordan|denmark|sweden|slovenia|portugal|greece|czech|mexico|malaysia)\b", re.I)

# Postal circles by PIN prefix (3 digits first, then 2 digits).
PIN3 = {"160": "Chandigarh", "246": "Uttarakhand", "248": "Uttarakhand", "249": "Uttarakhand", "263": "Uttarakhand",
        "403": "Goa", "605": "Puducherry", "737": "Sikkim", "744": "Andaman & Nicobar", "790": "Arunachal Pradesh",
        "791": "Arunachal Pradesh", "792": "Arunachal Pradesh", "793": "Meghalaya", "794": "Meghalaya", "795": "Manipur",
        "796": "Mizoram", "797": "Nagaland", "798": "Nagaland", "799": "Tripura", "814": "Jharkhand", "815": "Jharkhand",
        "816": "Jharkhand", "822": "Jharkhand", "825": "Jharkhand", "826": "Jharkhand", "827": "Jharkhand",
        "828": "Jharkhand", "829": "Jharkhand", "831": "Jharkhand", "832": "Jharkhand", "833": "Jharkhand",
        "834": "Jharkhand", "835": "Jharkhand", "396": "Gujarat"}
PIN2 = {"11": "Delhi", "12": "Haryana", "13": "Haryana", "14": "Punjab", "15": "Punjab", "16": "Punjab",
        "17": "Himachal Pradesh", "18": "Jammu & Kashmir", "19": "Jammu & Kashmir", "30": "Rajasthan", "31": "Rajasthan",
        "32": "Rajasthan", "33": "Rajasthan", "34": "Rajasthan", "36": "Gujarat", "37": "Gujarat", "38": "Gujarat",
        "39": "Gujarat", "40": "Maharashtra", "41": "Maharashtra", "42": "Maharashtra", "43": "Maharashtra",
        "44": "Maharashtra", "45": "Madhya Pradesh", "46": "Madhya Pradesh", "47": "Madhya Pradesh",
        "48": "Madhya Pradesh", "49": "Chhattisgarh", "50": "Telangana", "51": "Andhra Pradesh", "52": "Andhra Pradesh",
        "53": "Andhra Pradesh", "56": "Karnataka", "57": "Karnataka", "58": "Karnataka", "59": "Karnataka",
        "60": "Tamil Nadu", "61": "Tamil Nadu", "62": "Tamil Nadu", "63": "Tamil Nadu", "64": "Tamil Nadu",
        "67": "Kerala", "68": "Kerala", "69": "Kerala", "70": "West Bengal", "71": "West Bengal", "72": "West Bengal",
        "73": "West Bengal", "74": "West Bengal", "75": "Odisha", "76": "Odisha", "77": "Odisha", "78": "Assam",
        "80": "Bihar", "81": "Bihar", "82": "Bihar", "83": "Bihar", "84": "Bihar", "85": "Bihar"}
PIN2.update({str(p): "Uttar Pradesh" for p in range(20, 29)})

LEGAL = re.compile(r"\b(private\s+limited|pvt\.?\s*ltd\.?|p\.?\s*ltd\.?|limited|ltd\.?|llp|inc\.?|corporation|corp\.?|co\.)", re.I)
ADDRESS_START = re.compile(r"\b(plot|khasra|village|vill\.?|sector|survey|s\.?\s?no|gat\s?no|near|opp\.?|post|p\.o|"
                           r"industrial|ind\.?\s?area|phase|unit|road|rd\.|nh-?\d|kh\.?\s?no|house|h\.?\s?no|shed|"
                           r"block|street|mouza|tehsil|dist\.?|district|at\s*&|at\s+post)\b|\d", re.I)


def split_manufacturer(raw: str) -> tuple[str, str]:
    s = re.sub(r"\s+", " ", str(raw or "")).strip()
    s = PREFIX.sub("", s)                                   # "Mfg By: M/s. ..." -> "..."
    m = LEGAL.search(s)
    if m and m.start() < 90:
        name, addr = s[:m.end()], s[m.end():]
    else:
        head, _, tail = s.partition(",")
        cut = ADDRESS_START.search(head)
        if cut and cut.start() > 3:
            at = head.rfind(" ", 0, cut.start()) + 1   # cut at the start of the token, e.g. "D-12-13", not inside it
            at = at if at > 3 else cut.start()
            name, addr = head[:at], head[at:] + ("," + tail if tail else "")
        else:
            name, addr = head, tail
    name = re.sub(r"[\s,.;:-]+$", "", name).strip(" ,.")
    return name.title() if name.isupper() else name, addr.strip(" ,.")


def state_of(text: str) -> tuple[str, str]:
    """(state, how it was found). Looks at state and town names first, then the PIN code."""
    t = re.split(r"\b(?:mkt|mktd|mrk|mrkt|marketed|marketing)\.?\s*(?:by|:)", str(text or ""), flags=re.I)[0]  # the factory, not the marketer
    if FOREIGN.search(t):
        return "Outside India", "country name"
    # addresses run from specific to general ("..., Bangalore Highways, Kancheepuram Dist"), so the LAST place named wins
    last = [(max(m.end() for m in pat.finditer(t)), name) for name, pat in STATES if pat.search(t)]
    if last:
        return max(last)[1], "place name"
    pins = re.findall(r"(?<!\d)([1-8]\d{2})\s?(\d{3})(?!\d)", t)
    for a, b in reversed(pins):
        pin = a + b
        if pin[:3] in PIN3:
            return PIN3[pin[:3]], "PIN code"
        if pin[:2] in PIN2:
            return PIN2[pin[:2]], "PIN code"
    return "Unknown", "not found"


def name_key_v1(name: str) -> str:
    """The first normalisation, kept so the entity-resolution evaluation can show what the fixes changed."""
    k = name.lower()
    k = re.sub(r"\b(m/s|messrs)\b", " ", k)
    k = LEGAL.sub(" ", k)
    for a, b in [(r"pharmaceuticals?|pharmaceutical|pharmaceutics|pharmas?", "pharma"), (r"laborator(y|ies)|labs?\b", "lab"),
                 (r"health\s?care", "healthcare"), (r"industries|industry", "ind"), (r"formulations?", "formulation"),
                 (r"biotech(nology)?|bio-tech", "biotech"), (r"remedies", "remedy"), (r"\band\b|&", " ")]:
        k = re.sub(a, b, k)
    k = re.sub(r"[^a-z0-9 ]", " ", k)
    return re.sub(r"\s+", " ", k).strip()


# Normalisation rules, in order. Each was added for an error found in the labelled pairs (docs/ENTITY_RESOLUTION.md).
PREFIX = re.compile(r"^\s*((mfg|mfd|manufactured|mktd|marketed)\.?\s*(by)?\s*[:.\-]*\s*)?(m\s*/\s*s\.?|messrs\.?)?\s*", re.I)
KEY_RULES = [
    (r"\b(private|pvt|p)\.*\s*(limited|ltd)\b\.?|\b(limited|ltd|llp|inc|corporation|corp)\b\.?|\bco\.|\(p\)", " "),  # legal form
    (r"\b(pvt|private)\b", " "),                                    # "Pvt..Ltd" leftovers
    (r"\((i|india)\)|\bindia\b", " "),                              # "(I)" = "(India)" = "India"
    (r"ph[a-z]{1,4}c[ei]?u?t[a-z]*(\s+ls\b)?|pharmas?\b", "pharma"),  # Pharmaceuticals and its misspellings
    (r"laborator(y|ies)|\blabs?\b", "lab"), (r"health\s?care|healtchare|helathcare", "healthcare"),
    (r"industries|industry", "ind"), (r"formulations?", "formulation"), (r"bio[\s-]?tech(nology)?", "biotech"),
    (r"life\s?sciences?", "lifescience"), (r"bio[\s-]?sciences?", "bioscience"), (r"remedies", "remedy"),
    (r"\band\b|&", " "), (r"[^a-z0-9 ]", " "),
    (r"(\s+(k\s*no|kh\s*no|no|unit\s*[ivx\d]*))+\s*$", " "),         # address residue at the end: "... K. No", "... Unit-II"
]


def name_key(name: str) -> str:
    """Normalised manufacturer name used to group spellings of the same firm."""
    k = PREFIX.sub("", str(name or "")).lower()
    for a, b in KEY_RULES:
        k = re.sub(a, b, k)
    return re.sub(r"\s+", " ", k).strip()


def compact(key: str) -> str:
    """The key with spaces removed, so "NitinLifesciences" equals "Nitin Life Sciences"."""
    return key.replace(" ", "")


# ------------------------------------------------------------------ products
FORMS = [
    ("IV fluid", r"sodium chloride.*(inj|infusion)|dextrose.*(inj|infusion)|ringer|normal saline|\bi\.?v\.?\s+fluid|glucose.*infusion"),
    ("Injection", r"injection|\binj\b|infusion|vial|ampoule|for injection"),
    ("Vaccine / biological", r"vaccine|serum|immunoglobulin|antitoxin|insulin|albumin|heparin|erythropoietin"),
    ("Tablet", r"tablet|\btabs?\b|caplet"),
    ("Capsule", r"capsule|\bcaps?\b|softgel"),
    ("Syrup", r"syrup|linctus|elixir"),
    ("Suspension", r"suspension"),
    ("Oral solution / drops", r"oral solution|oral liquid|drops|solution|liquid|mouthwash"),
    ("Cream / ointment / gel", r"cream|ointment|\bgel\b|lotion|liniment|balm"),
    ("Powder / sachet", r"powder|sachet|granules|o\.?r\.?s|oral rehydration"),
    ("Inhaler / spray", r"inhaler|spray|respule|rotacap|nebuli"),
    ("Disinfectant", r"chlorine|sanitizer|sanitiser|disinfectant|hand rub|bleaching|hypochlorite|povidone|antiseptic"),
    ("Medical device / consumable", r"gauze|bandage|cotton|suture|syringe|needle|catheter|glove|cannula|condom|plaster|dressing|test kit|strip"),
]
FORMS = [(n, re.compile(p, re.I)) for n, p in FORMS]

CLASSES = [
    ("Antibiotic / anti-infective", r"cillin|cef|cefi|cepha|penem|mycin|micin|floxacin|cycline|azole\b|sulfa|trimethoprim|metronidazole|tinidazole|ornidazole|linezolid|clavul|nitrofurantoin|cotrimoxazole|acyclovir|fluconazole|ketoconazole|clotrimazole|terbinafine|vancomycin|colistin|chloramphenicol"),
    ("Pain / fever / inflammation", r"paracetamol|acetaminophen|diclofenac|aceclofenac|ibuprofen|nimesulide|naproxen|mefenamic|ketorolac|tramadol|piroxicam|etoricoxib|aspirin|serratiopeptidase|indomethacin|thiocolchicoside"),
    ("Cough / cold / allergy", r"dextromethorphan|chlorphenir|phenylephrine|cetirizine|levocetirizine|ambroxol|bromhexine|guaifenesin|montelukast|fexofenadine|loratadine|diphenhydramine|terbutaline|salbutamol|cough|codeine|pheniramine|promethazine"),
    ("Diabetes", r"metformin|glimepiride|gliclazide|glibenclamide|sitagliptin|vildagliptin|teneligliptin|dapagliflozin|empagliflozin|pioglitazone|insulin|voglibose|acarbose"),
    ("Heart / blood pressure / lipids", r"amlodipine|telmisartan|losartan|olmesartan|atenolol|metoprolol|bisoprolol|propranolol|ramipril|enalapril|atorvastatin|rosuvastatin|clopidogrel|nifedipine|furosemide|hydrochlorothiazide|spironolactone|digoxin|isosorbide|torsemide|cilnidipine|warfarin|ticagrelor"),
    ("Gastro-intestinal", r"pantoprazole|omeprazole|rabeprazole|esomeprazole|ranitidine|famotidine|domperidone|ondansetron|antacid|aluminium hydroxide|magnesium hydroxide|simethicone|loperamide|lactulose|bisacodyl|sucralfate|racecadotril|itopride|dicyclomine|drotaverine|hyoscine"),
    ("Vitamins / minerals / nutrition", r"vitamin|calcium|cholecalciferol|ferrous|iron|folic|zinc|multivitamin|methylcobalamin|cyanocobalamin|b-complex|b complex|thiamine|pyridoxine|ascorbic|protein|electrolyte|potassium chloride"),
    ("Antimalarial / antiparasitic", r"chloroquine|primaquine|artesunate|artemether|lumefantrine|quinine|mefloquine|albendazole|mebendazole|ivermectin|praziquantel|pyrimethamine"),
    ("Steroid / hormone", r"dexamethasone|prednisolone|methylprednisolone|hydrocortisone|betamethasone|deflazacort|thyroxine|levothyroxine|progesterone|estradiol|oxytocin|testosterone|norethisterone|misoprostol"),
    ("Nervous system / mental health", r"phenytoin|levetiracetam|valproate|valproic|carbamazepine|gabapentin|pregabalin|alprazolam|clonazepam|diazepam|lorazepam|amitriptyline|escitalopram|sertraline|fluoxetine|olanzapine|risperidone|haloperidol|quetiapine|donepezil|betahistine|cinnarizine|levodopa"),
    ("IV fluids / electrolytes", r"sodium chloride|dextrose|ringer|glucose|mannitol|sodium bicarbonate|water for injection"),
    ("Anaesthesia / critical care", r"lignocaine|lidocaine|bupivacaine|propofol|ketamine|atropine|adrenaline|epinephrine|noradrenaline|dopamine|midazolam|succinylcholine|vecuronium|neostigmine|ondansetron injection"),
    ("TB / HIV / antivirals", r"rifampicin|isoniazid|pyrazinamide|ethambutol|tenofovir|lamivudine|efavirenz|dolutegravir|zidovudine|nevirapine|oseltamivir|favipiravir"),
    ("Disinfectant / antiseptic", r"chlorine|sanitizer|sanitiser|povidone|chlorhexidine|hypochlorite|alcohol|antiseptic|bleaching"),
]
CLASSES = [(n, re.compile(p, re.I)) for n, p in CLASSES]

NOISE = re.compile(r"\b(i\.?p\.?|b\.?p\.?|u\.?s\.?p\.?|ph\.?\s?eur\.?|tablets?|capsules?|injections?|syrups?|suspensions?|"
                   r"oral|solution|for|film|coated|f\.?c\.?|sustained|extended|prolonged|release|s\.?r\.?|e\.?r\.?|"
                   r"gastro|resistant|dispersible|chewable|uncoated|enteric|sterile|vet|veterinary|each|contains|"
                   r"usp|ip|bp|mg|ml|mcg|gm|g|iu|w/v|w/w|v/v)\b", re.I)


def clean_product(raw: str) -> dict:
    s = re.sub(r"\s+", " ", str(raw or "")).strip()
    inner = re.findall(r"\(([^()]{6,})\)", s)
    descriptive = [x for x in inner if re.search(r"tablet|capsule|injection|syrup|suspension|i\.?p\.?|b\.?p\.?|solution|cream|gel|mg", x, re.I)]
    outside = re.sub(r"\([^()]*\)", " ", s)

    def tidy(base: str) -> str:
        g = re.sub(r"\d+(\.\d+)?\s*(mg|ml|mcg|gm|g|iu|%|lakh|units?|unit)\b", " ", base, flags=re.I)
        g = NOISE.sub(" ", g)
        g = re.sub(r"[^A-Za-z&+,/ \-]", " ", g)
        return re.sub(r"\s+", " ", g).strip(" ,-/&+")
    generic = tidy(descriptive[0]) if descriptive else ""
    if len(re.sub(r"[^A-Za-z]", "", generic)) < 3:          # the bracket held only a dose, e.g. "(500 mg + 250 IU)"
        generic = tidy(outside)
    generic = generic.title()[:80] if generic else s.title()[:80]
    form = next((n for n, p in FORMS if p.search(s)), "Other")
    tclass = next((n for n, p in CLASSES if p.search(s)), "Other / unclassified")
    return {"generic_name": generic, "dosage_form": form, "therapeutic_class": tclass}


# ------------------------------------------------------------------ failures
FAILURES = [
    ("DEG/EG contamination", "critical", r"diethylene glycol|ethylene glycol|\bdeg\b|\beg\b"),
    ("Sterility", "critical", r"steril"),
    ("Adulterated", "critical", r"adulterat"),
    ("Endotoxin / pyrogen", "critical", r"endotoxin|pyrogen|\bbet\b"),
    ("Microbial contamination", "critical", r"microb|bacterial count|fungal|yeast|mould|mold|e\.?\s?coli|salmonella"),
    ("Spurious (fake)", "critical", r"spurious|counterfeit"),
    ("Identity test failed", "critical", r"identif|identity|does not contain|not contain|absence of|absent"),
    ("Assay (strength)", "major", r"assay|content of|(?<!net )(?<!water )\bcontent\b|potency|activity|strength"),
    ("Dissolution", "major", r"dissolution"),
    ("Impurities", "major", r"related substance|impurit|degradation"),
    ("Particulate matter", "major", r"particulate|particle|clarity|visible"),
    ("Uniformity", "major", r"uniformi?ty|uniforme?ly"),
    ("Disintegration", "minor", r"disintegration"),
    ("Description / appearance", "minor", r"description|appearance|colou?r|odou?r|physical"),
    ("pH", "minor", r"\bph\b"),
    ("Weight / volume", "minor", r"weight|volume|fill|average|net content"),
    ("Labelling / misbranding", "minor", r"label|misbrand|mis-brand"),
    ("Water / moisture", "minor", r"water|moisture|loss on drying"),
]
FAILURES = [(n, sev, re.compile(p, re.I)) for n, sev, p in FAILURES]
SEVERITY_RANK = {"critical": 3, "major": 2, "minor": 1, "unclassified": 0}


def classify_failure(raw: str) -> dict:
    s = str(raw or "")
    found = [(n, sev) for n, sev, p in FAILURES if p.search(s)]
    if not found:
        return {"failure_categories": "Other", "primary_failure": "Other", "severity": "unclassified"}
    primary = max(found, key=lambda x: SEVERITY_RANK[x[1]])
    return {"failure_categories": "; ".join(n for n, _ in found), "primary_failure": primary[0], "severity": primary[1]}
