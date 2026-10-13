# DawaDrishti (दवा दृष्टि): a national memory of medicine quality

**Two in three failed medicine batches in India come from a factory that was already on the national failure list.**

We joined nine years of CDSCO's published "not of standard quality" alerts by manufacturer:
- **64.9%** of 6,442 failed batches came from a manufacturing unit that already had an alert in an earlier month (95% CI 62.2–67.4%).
- Half of those repeats were caught by a lab, or in a state, that had never caught that unit before.

The record exists, but no buyer's ERP reads it. DawaDrishti turns it into a **lookup any public buyer's ERP can call** before a purchase order or a goods receipt.

Open source (MIT) · Python · DuckDB · scikit-learn · FastAPI · React · COMMIT FOR GOOD 2026 (AI for Resilient and Sustainable Supply Chains)

<!-- LIVE_DEMO -->

[Proposal (PDF)](docs/pdf/DawaDrishti_Proposal.pdf) · [Evaluation](docs/EVALUATION.md) · [Entity resolution](docs/ENTITY_RESOLUTION.md) · [Naming policy](docs/NAMING_POLICY.md) · [Assumptions](docs/ASSUMPTIONS.md) · [Architecture](docs/ARCHITECTURE.md)

---

## The problem

- **Scale.** 3,104 drug samples were declared not of standard quality in 2024–25, out of 1.16 lakh tested (Lok Sabha, via [IndiaMedToday](https://indiamedtoday.com/over-3000-drug-samples-declared-not-of-standard-quality-in-2024-25-nadda/)).
- **Coldrif.** 24 children's deaths had been reported by 15 October 2025 after they took Coldrif cough syrup, which was contaminated with diethylene glycol (ETV Bharat).
- **One state supplier.** Its samples failed 40 times in Rajasthan's state testing (2021–23). It was banned for a year, then reinstated ([Down To Earth](https://www.downtoearth.org.in/amp/story/health/cough-syrup-deaths-in-rajasthan-families-allege-negligence-while-government-denies-link-to-medicine)).
- **Where the information sits.** CDSCO publishes every failed batch, and buyers run their own ERPs (DVDMS, e-Aushadhi, state corporations' systems). Nothing connects the two, so a failure found in one state is invisible to a buyer in another.

## What it is

**A public-record aggregator with a risk signal for buyers, not a blacklist, and not a new ERP.**

| Part | What it does | Data |
|---|---|---|
| **Headline study** | Repeat share, lead time, detection elsewhere and concentration, with a cluster-bootstrap CI and robustness across five matching rules | Real |
| **Extraction + audit** | Portal JSON (2019–26) and PDF alerts (2017–18). The PDF parser is checked against the portal: 96.9% row precision, 96.7–99.8% field agreement | Real |
| **Entity resolution** | 5,521 name strings become 1,994 units and 1,797 firms. Evaluated on held-out labelled pairs (precision 1.00, recall 0.63), with a human review queue for the 80–92 band | Real |
| **Lookup API** `GET /api/v1/lookup` | **Public view:** the published record, with an as-of date, what the data does not contain, a correction link and `regulatory_action`. **Buyer view:** adds a graded response (pause / test every batch / prefer alternatives / no record), a future-regulatory-attention score and alternatives | Real record; alternatives use simulated supplier masters |
| **Reference buyer console** | Two moments inside an ERP. (1) The PO is checked by the graded response, with supplier concentration and days of cover beside it. (2) A received batch cannot be issued until the lab clears it | Simulated buyers |
| **Conformance engine** | Declarative rules (precedence, response, requires) plus process discovery. Identical counts to hand-written checks; reads XES for BPI 2019 | Simulated log (BPI run pending) |
| **Patterns and models** | FP-Growth rules, archetypes, spikes, geography. An attention model (AUC 0.774, with a confound check) and batch risk (simulated) | Real / simulated |
| **Questions** | Nine reviewed SQL templates with checked parameters. A keyword parser or Gemini picks the template; no model writes SQL or text about a firm | Real |

## Results

| What | Result |
|---|---|
| Failed batches whose unit was already on record | **64.9%** (CI 62.2–67.4%); 59.0% of critical failures |
| Median time from a unit's first failure to its next | 8 months |
| Repeats caught by a new lab / in a new state | 52.6% / 52.8% |
| Share of failures from the top 10% of units | 47.5% |
| The same share with exact name matching | 4.2%, so entity resolution is the whole game |
| Coldrif, Maiden, Kaysons | **No** national alert before the incident. The memory must also take state-lab and buyer results |
| Attention model vs the best simple rule | AUC 0.774 vs 0.745. On the top 50 alone, "most recent failure" wins (84% vs 76%), and we say so |
| Simulated shared memory vs isolated ERPs | Orders to debarred suppliers −81%, failed batches received −30% |

Full method and tables: [docs/EVALUATION.md](docs/EVALUATION.md).

## Run it

```bash
git clone https://github.com/AbhishekJadli007/dawadrishti.git && cd dawadrishti
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cd web && npm install && npm run build && cd ..
uvicorn api.main:app --port 8000          # open http://localhost:8000 · API docs at /docs
```

The built warehouse, ERP database, models and study results are committed, so the app runs straight away. To rebuild from source:

```bash
python -m dawadrishti fetch    # re-download CDSCO alerts (portal JSON + PDFs), ~5 min
python -m dawadrishti build    # stage -> ERP history -> warehouse -> mining -> models -> study -> evaluations (~1.5 min)
python -m dawadrishti ask "Which antibiotic tablets from Gujarat failed since 2024?"
python -m dawadrishti.mining.conformance --bpi BPI_Challenge_2019.xes   # external validation, once downloaded from 4TU
pytest                                               # 16 tests
```

Optional: put `GEMINI_API_KEY=...` in `.env` (free key at aistudio.google.com/apikey) to let Gemini choose question templates. Everything works without it.

```bash
curl "http://localhost:8000/api/v1/lookup?q=Nestor%20Pharmaceuticals%20Ltd&view=buyer"
```

## Data

| Data | Real or simulated | Source and licence |
|---|---|---|
| Failed-batch alerts, 2019–2026 (6,652 records) | **Real** | CDSCO public NSQ portal, `cdscoonline.gov.in` (Government of India public information) |
| Failed-batch alerts, 2017–2018 | **Real** | CDSCO monthly alert PDFs |
| Entity-resolution labels (200 pairs) | Labelled by the AI assistant, **awaiting human review** | `data/er/labelled_pairs.csv` |
| ERP transactions of 5 buyers (orders, batches, QC, issues, recalls, payments, debarments) | **Simulated**, seeded | `dawadrishti/erp/simulate.py`. Buyer names are fictional. Supplier names and their national records are real; their orders and debarments are simulated and labelled so in the app |

## Limitations

- **Alerts list failures, not tests.** A failure rate per manufacturer cannot be computed; we measure recurrence on the record.
- **Sampling is uneven.** Heavily sampled states appear more often. The attention model predicts regulatory attention, not true quality.
- **Labels.** The entity-resolution labels are the assistant's until people review them. Recall is 0.63 on hard pairs, so some histories are split. That makes the headline conservative.
- **BPI Challenge 2019 validation is pending.** 4TU was unreachable from the build machine.
- **Contribution route.** The memory needs buyers and state labs to send results back; that route is designed but not built. Kaysons' failures never reached the national list.

## Project layout

```
dawadrishti/etl/        portal.py · crawl.py · parse_pdf.py · clean.py · stage.py · entities.py · audit.py
dawadrishti/study.py    headline study            dawadrishti/entity_eval.py  entity-resolution evaluation
dawadrishti/memory.py   lookup API (record, graded response, alternatives)
dawadrishti/erp/        schema.py · service.py · simulate.py   (reference buyer console)
dawadrishti/mining/     conformance.py · process.py · patterns.py · risk.py
dawadrishti/ai/ask.py   question templates      dawadrishti/warehouse.py  DuckDB star schema
api/main.py             FastAPI · web/ React app · tests/ pytest · deploy/ Hugging Face Space
```

## Author

Built by **Abhishek Jadli** ([@AbhishekJadli007](https://github.com/AbhishekJadli007)) for COMMIT FOR GOOD 2026.

## Licence

MIT. See [LICENSE](LICENSE). CDSCO data is Government of India public information; see [ACKNOWLEDGEMENTS.md](ACKNOWLEDGEMENTS.md).

*DawaDrishti shows published records and decision-support signals. It makes no finding against any manufacturer. To correct a record, open a [correction request](.github/ISSUE_TEMPLATE/correction.md).*
