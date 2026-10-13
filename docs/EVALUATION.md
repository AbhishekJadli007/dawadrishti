# Evaluation

Every number below is reproduced by `python -m dawadrishti build`, which writes the files in `artifacts/`. Every result is labelled **real** (CDSCO's published alerts) or **simulated** (the five fictional buyers in the reference console). Data runs to August 2026; the build was run on 13 October 2026.

| # | What | Data | Result |
|---|---|---|---|
| 1 | **Do failed batches come from units already on the national record?** | real | **64.9%** of failed batches did (95% CI 62.2–67.4%) |
| 2 | Is the PDF parser reading alerts correctly? | real | 96.9% of parsed rows match the portal; fields agree 96.7–99.8% |
| 3 | Are names grouped into the right factories? | real, labelled pairs | Precision 1.00, recall 0.63 on held-out hard pairs; 0.98 with human review |
| 4 | Can the next 6 months of alerts be predicted? | real | AUC 0.774, against 0.745 for the best simple rule; not just state sampling |
| 5 | Does the conformance engine count correctly? | simulated log | Declarative rules give identical counts to hand-written checks; BPI 2019 run pending |
| 6 | Does test-the-riskiest-first help a buyer's lab? | simulated | 69% of failing batches caught in the first 30% of tests, against 28% first-in-first-out |
| 7 | What would sharing the memory change? | simulated | Orders to debarred suppliers −81%, failed batches received −30% |

---

## 1. The headline study: does a national memory have anything to remember? (real)

`dawadrishti/study.py` → `artifacts/memory_study.json`. CDSCO NSQ alerts, Sep 2017 to Aug 2026, 6,442 failed batches from 1,914 manufacturing units. Excluded:
- records whose maker is unknown or under investigation;
- fakes whose named firm denied making them;
- records whose manufacturer field names the supplying public buyer instead of a maker;
- records with no state.

The 112 records of makers outside India are kept.

| Measure | Result |
|---|---|
| **Failed batches whose unit already had an alert in an earlier month** | **64.9%** (95% CI 62.2–67.4%, cluster bootstrap over units, 1,000 resamples) |
| The same, among critical failures (contamination, sterility, endotoxin, adulteration, fakes) | 59.0% |
| Units with at least one repeat | 841 of 1,914 |
| Median months from a unit's first failure to its next | 8.0 |
| Median months between consecutive failures of a unit | 3.9 |
| Median months a repeat came after the unit first appeared | 32.1 |
| Repeats caught by a lab that had never caught that unit before | 52.6% |
| Repeats caught in a state that had never caught that unit before | 52.8% (of the 1,081 repeats where a state lab is named) |
| Share of all failed batches from the top 10% of units | 47.5% (Gini 0.55) |
| Units by number of failed batches | 1: 963 · 2–4: 627 · 5–9: 197 · 10+: 127 |

**Sensitivity to the matching rule.** The result does not depend on one choice of matching rule:

| Matching rule | Units | Repeat share | Months to next |
|---|---|---|---|
| Exact string | 5,399 | 4.2% | 2.0 |
| Normalised name, same state | 2,030 | 62.8% | 8.0 |
| **Fuzzy ≥92, same state (default)** | **1,914** | **64.9%** | **8.0** |
| Fuzzy ≥92, units joined across states (firm) | 1,758 | 67.5% | 9.0 |
| Loose: fuzzy ≥85, any state | 1,740 | 67.8% | 9.0 |

**Worked cases.** The national alerts alone would not have warned anyone about these three:

| Case | Incident | National alerts before | Alerts in total | Reading |
|---|---|---|---|---|
| Sresan Pharmaceutical (Coldrif) | Oct 2025 | 0 | 11 | First alert in Oct 2025, after the deaths |
| Maiden Pharmaceuticals (The Gambia) | Oct 2022 | 0 | 6 | First alert in Dec 2022 |
| Kaysons Pharma (Rajasthan) | 2025 | 0 | 0 | 40 failures in state testing (2021–23) never reached the national list |

These cases are the reason the memory must also take state-lab and buyer test results, not only CDSCO's list.

**What this study cannot say.**
- **No failure rates.** The alerts list failures, not tests.
- **Uneven sampling.** Heavily sampled states produce more repeats.
- **Invisible history.** Failures before Sep 2017 are not in the data, so some "first" failures are really repeats. That undercounts repeats.
- **Missed merges** also undercount repeats; see section 3.

## 2. Extraction audit: PDF parser vs CDSCO's structured portal (real)

`dawadrishti/etl/audit.py` → `artifacts/extraction_audit.json`.
- **Why it matters.** Alerts before 2019 exist only as PDFs.
- **Method.** For 19 later months CDSCO published both a PDF and portal JSON. We parsed 27 of those PDFs and compared them, row by row on batch number, with portal rows from the same type of lab (central or state) and month (±1).

| Measure | Result |
|---|---|
| Parsed PDF rows | 1,349 |
| Rows that match a portal row (precision) | 96.9% |
| Portal rows found in the PDFs (recall, a lower bound) | 88.7% of 1,450 |

| Field (1,307 matched rows) | Agreement | Missing in the PDF |
|---|---|---|
| Product name | 98.7% | 0 |
| Manufacturer (resolved name) | 99.1% | 0 |
| State (derived from the address) | 99.8% | 0 |
| NSQ result text | 98.8% | 0 |
| Manufacturing date | 97.7% | 26 |
| Expiry date | 96.7% | 43 |

**Bugs the audit found and we fixed:**
- **Split header words.** pdfplumber read "Manufacturing Date" as "Manufactu ring Date", so the manufacturing date was missing in 74% of rows. It is now missing in 2%.
- **Letter-spaced text.** Text such as "P h a r m a c e t i c a l s" is now rejoined.

**Disagreements that remain** are mostly differences in the source: "3 yrs from the date of mfg" against a computed month, and Excel serial dates printed in a PDF.

## 3. Entity resolution (real alerts, labelled pairs)

Full write-up: [ENTITY_RESOLUTION.md](ENTITY_RESOLUTION.md).

| Matcher (held-out test pairs, firm level) | Precision | Recall | F1 |
|---|---|---|---|
| Exact name | 1.00 | 0.00 | 0.00 |
| Fuzzy ≥92, v1 rules | 1.00 | 0.48 | 0.65 |
| **Fuzzy ≥92, v2 rules (in use)** | **1.00** | **0.63** | **0.77** |
| v2 + human review of the 80–92 band | (reviewer) | 0.98 | |

- **Labels.** 120 development and 80 test pairs, labelled by the AI assistant and awaiting human review.
- **Why the threshold is high.** It favours precision, because a false merge would put one firm's failures on another firm's record.
- **The review queue.** 206 pairs; it is on the **Quality** page.

## 4. Future regulatory attention: which units will appear in the next 6 months of alerts? (real)

`dawadrishti/mining/risk.py`.
- **Training.** Monthly snapshots, Jan 2021 to Sep 2025.
- **Test.** A cutoff of 1 Mar 2026, scored against the real alerts of Mar–Aug 2026: 1,737 units, of which 386 appeared (base rate 22.2%).

| Method | AUC | Top-50 hit rate | Top-200 recall |
|---|---|---|---|
| **Attention model (gradient boosting)** | **0.774** | 76% | **32.1%** |
| Most past failures | 0.745 | 72% | 30.3% |
| Most recent failure | 0.735 | **84%** | 28.2% |
| Random | 0.500 | 18% | 11.4% |

**Honest reading.**
- The model ranks the whole list best.
- On the top 50 alone, "most recent failure" does better (84% against 76%). A drug controller planning only 50 samples should use the simple rule.
- **The target is regulatory attention, not true quality.** The model predicts that a unit is sampled *and* fails, and sampling depends on where inspectors look. The model is renamed for this reason, and its score is never shown on public pages.

**Confound check: is the model only learning which states are sampled most?**

| Group | Units | Base rate | Model AUC | "Most recent failure" AUC |
|---|---|---|---|---|
| Units in HP, Uttarakhand, Gujarat (most sampled) | 832 | 28.7% | 0.758 | 0.705 |
| Units in all other states | 905 | 16.2% | 0.756 | **0.763** |
| A model that knows only the unit's state | | | 0.601 | |

- **State matters, but it is not what the model learns.** State alone carries some signal (0.601), but the model ranks equally well inside and outside the heavily sampled states.
- **Outside them, the simple rule wins.** "Most recent failure" is slightly better there, and we report that rather than hide it.

## 5. Conformance engine (simulated log; external validation pending)

`dawadrishti/mining/conformance.py`.
- **How rules work.** Rules are data: precedence, response within N days, and requires. They can be scoped to a sub-case (`given`) or to case attributes (`when`).
- **Two checks.** The same engine runs on our ERP log and on any XES or CSV log.

**Cross-check on the simulated log (6,100 cases).** The declarative rules give the same counts as the hand-written checks in `process.py`:

| Rule | Hand-written | Declarative |
|---|---|---|
| R1 Issued before quality clearance | 628 | 628 |
| R2 Failed batch already issued, not recalled within 2 days | 18 | 18 |
| R3 Sample sent to lab without blind coding | 129 | 129 |
| R4 Payment released before clearance | 209 | 209 |
| R6 Lab turnaround over 21 days | 1,467 | 1,467 |

R5 (an order placed while another buyer's debarment is in force) needs the debarment register, so it stays hand-written: 818 cases.

**External validation on BPI Challenge 2019** (the public SAP purchase-to-pay log, 4TU.ResearchData): **pending.**
- **Why.** 4TU could not be reached from the build machine on 13 Oct 2026: DNS resolved, but the connection never completed.
- **What is ready.** The reader, which handles XES, .xes.gz and the CSV export, and four P2P rules mapped to ours:
  - P1: invoice cleared before goods receipt, about R4;
  - P2: invoice recorded before goods receipt where the contract says after;
  - P3: goods received before the purchase-order item existed;
  - P4: invoice cleared without an invoice receipt.
- **Tests.** Both pass on a synthetic XES file (`tests/test_conformance.py`).
- **To run it:**

  ```bash
  python -m dawadrishti.mining.conformance --bpi /path/to/BPI_Challenge_2019.xes   # -> artifacts/bpi2019_conformance.json
  ```

## 6. Batch risk: test the riskiest batch first (simulated)

- **Training.** Batches received in 2025 by the simulated buyers.
- **Test.** Jan–Aug 2026: 2,196 batches, 149 of which failed.
- **The question.** If the lab can test only 30% of batches first, how many of the failing ones are caught early?

| Order | AUC | Failing batches caught in the first 30% of tests |
|---|---|---|
| **Risk order** | 0.748 | **69.1%** |
| First in, first out | 0.486 | 27.5% |
| Random | 0.476 | 22.8% |

**Caution.** Failures were simulated from each supplier's real national record, so this shows the method works. It does not measure a real buyer.

## 7. The network effect: isolated ERPs vs a shared memory (simulated)

The same 20 months were replayed twice with the same random seed:
- **isolated:** each buyer sees only its own results;
- **shared memory:** at purchase-order time, buyers see national alerts and every buyer's debarments.

Debarments last 12 months.

| Measure | Isolated | Shared memory | Change |
|---|---|---|---|
| Orders to a supplier debarred by another buyer | 847 | 157 | −81% |
| Failed batches received | 388 | 273 | −30% |
| Orders placed after the supplier failed at another buyer | 2,036 | 1,583 | −22% |

**Caution.** This is a property of the simulation's assumptions ([ASSUMPTIONS.md](ASSUMPTIONS.md)), not a measured outcome.

## 8. Process mining findings (simulated: they demonstrate the method)

**Setup.** 6,100 cases and 66,791 events. The rule-breaking was simulated on purpose, so finding it tests the miner, not the buyers.

**Conformance by buyer.** Share of cases that broke no rule:
- National agency: 79.9%
- Southern: 79.5%
- Western: 63.8%
- Northern: 30.5%
- Eastern: 22.0%

**Root cause.** Stock is issued before clearance in 2.8% of cases when the lab answers within a week, rising to 34.9% at 45 days or more. Lab turnaround is the strongest driver in the decision tree (importance 0.76).

## 9. Patterns in the national record (real)

`dawadrishti/mining/patterns.py`.

**Repeat units.**
- 847 units failed more than once. Together they account for 79.7% of failed batches, counting their first failure.
- That differs from the study's 64.9%, which counts only failures *after* the unit was on record.
- Of failures, 51.9% were followed by another failure from the same unit within 12 months.

**Association rules (FP-Growth).** These are where to point the lab, not findings against any firm.
- Injections fail on particulate matter in 30.4% of cases (lift 7.8), and on sterility in 19.5% (lift 4.5).
- Antibiotic tablets fail on dissolution in 48.7% of cases (lift 2.2).

**Geography.** By the manufacturer's address: Himachal Pradesh 30.4%, Uttarakhand 15.5%, Gujarat 9.3%. These shares mix production volume with sampling effort.

## 10. Not evaluated yet

- **Human agreement on the entity-resolution labels.** All 200 labels are the assistant's.
- **BPI Challenge 2019.** The run is pending because 4TU was unreachable (section 5).
- **Real buyers.** No real buyer data is used. The console, network effect and batch-risk results are simulated.
- **Optional LLM template choice.** Its accuracy is not measured. The keyword parser is the default, and both choose from the same nine checked templates.
