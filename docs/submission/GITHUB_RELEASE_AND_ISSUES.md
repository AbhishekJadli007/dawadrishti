# GitHub release and issues (copy and paste)

## Release v1.0

On GitHub, go to **Releases**, then **Draft a new release**. Choose the tag `v1.0`.

**Title:** `DawaDrishti v1.0 — COMMIT FOR GOOD 2026 submission`

**Notes:**

```
A national memory of India's failed medicine batches, with a lookup that any public buyer's ERP can call before buying.

Live demo: https://dawadrishti.onrender.com

What this version does
- Extracts CDSCO's "not of standard quality" alerts (portal 2019-2026, PDFs 2017-2018) and audits the PDF reader against the portal (96.9% of rows match).
- Resolves 5,521 manufacturer name strings into 1,994 factories, evaluated on held-out labelled pairs (precision 1.00), with a human review queue.
- Headline study: 64.9% of failed batches came from a factory already on the national list (95% CI 62.2-67.4%).
- Lookup API (/api/v1/lookup): the public record, with as-of date, data limits and a correction route; the buyer view adds a graded response, a model score and alternatives. An exact-batch check holds a batch already on the list.
- Reference buyer console (simulated buyers): purchase order -> goods receipt -> release, with release blocked until the lab clears the batch.
- Declarative conformance engine, checked against hand-written rules and on the public BPI Challenge 2019 SAP log (all 4 published counts reproduced).
- Models tested against simple baselines, with confound checks. Questions answered through reviewed query templates (Gemini optional).

Documents: docs/pdf/DawaDrishti_Solution_Document.pdf, DawaDrishti_Solution_Brief.pdf, DawaDrishti_Presentation.pdf
Run: docker build -t dawadrishti . && docker run -p 8000:8000 dawadrishti
Licence: MIT. CDSCO data is Government of India public information.
```

Attach the three PDFs from `docs/pdf/` to the release (drag them into the assets box).

---

## Issues to open

Open each from **Issues**, then **New issue**. Add the label `good first issue` where it says so.

### 1. Review the 200 entity-resolution labels

Label: `help wanted`

```
The 200 labelled name pairs in data/er/labelled_pairs.csv were labelled by an AI assistant from names and addresses only.
They need a human review before the evaluation can claim human-validated precision and recall.

How:
  python -m dawadrishti.entity_eval --review        # blind: you don't see the existing label
  python -m dawadrishti.entity_eval                 # re-scores with your labels and reports agreement

Done when: all 200 pairs have a human_label, and docs/ENTITY_RESOLUTION.md reports human-vs-assistant agreement.
```

### 2. Let state labs and buyers send their test results in

Label: `enhancement`

```
Coldrif, Maiden and Kaysons had no national alert before their incidents. Their failures were found in state testing that never
reached CDSCO's national list. The memory needs a contribution route.

Proposal:
- POST /api/v1/results (authenticated per lab or buyer): manufacturer, product, batch, test, result, lab, date, evidence link
- Contributed results are shown separately from CDSCO alerts, labelled with their source, and pass the same name resolution
- Include them in the graded response only once verified

See docs/ARCHITECTURE.md ("results shared back") and docs/NAMING_POLICY.md.
```

### 3. Map products to WHO ATC codes and India's NLEM

Label: `good first issue`

```
dawadrishti/etl/clean.py classifies products into 14 keyword-based therapeutic classes (80% classified).
Mapping generic names to WHO ATC codes, and flagging medicines on India's National List of Essential Medicines,
would make the patterns and the "alternatives" far more precise.

Start with clean.clean_product(); add a small mapping table under data/ with its source and licence.
```

### 4. A DVDMS / e-Aushadhi connector example

Label: `enhancement`

```
Show how an existing ERP calls the lookup at purchase-order and goods-receipt time.
A small, documented example (Python or Java) that:
- reads a purchase order (supplier name, molecule) and calls /api/v1/lookup?view=buyer
- reads a goods receipt (batch number) and calls the lookup with &batch=
- maps the graded response (0-3) to an ERP action (allow / warn / require override)

Put it under examples/erp_connector/ with a README.
```
