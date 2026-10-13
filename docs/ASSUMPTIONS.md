# Data, cleaning rules and assumptions

## Real data (national)

| Source | What | Records |
|---|---|---|
| CDSCO public NSQ portal (`cdscoonline.gov.in/CDSCO/filteredNsqDrugTable`, `filteredSpuriousDrugTable`), the same JSON the public page loads, cached in `data/raw/portal/` | Every failed batch, Jan 2019 – Aug 2026: product, batch, dates, manufacturer + address, NSQ result, central or state lab, reporting month; spurious list with the firm's reply | 6,604 NSQ + 48 spurious |
| CDSCO monthly alert PDFs (`cdsco.gov.in` Alerts), parsed with pdfplumber | 2017–2018 months not on the portal | 7 |
| Lok Sabha answer (via IndiaMedToday, Dec 2025) | 1.16 lakh samples tested, 3,104 NSQ in 2024–25: the national failure rate (~2.7%) | — |

## Cleaning rules (`dawadrishti/etl/clean.py`, rule-based)

- **Manufacturer name vs address.**
  - Strip "M/s." and "Mfg By:".
  - If a legal suffix (Pvt Ltd, Limited, LLP…) appears in the first 90 characters, the name ends there.
  - Otherwise the name ends at the first comma, or at the start of the first address token (plot, khasra, village, sector, a number).
- **State.**
  - Text after "Marketed by" / "Mkt by" is ignored, because it is the marketer, not the factory.
  - State names and known manufacturing towns (Baddi, Selaqui, Pithampur…) are then matched, and **the last one in the address wins**. Addresses run from specific to general: "…Bangalore Highways, Kancheepuram Dist" is in Tamil Nadu.
  - Then the PIN code (3-digit and 2-digit postal-circle prefixes).
  - Country names mark the maker as "Outside India". These 112 records are kept and shown.
  - Found for 97.4% of records.
- **Product.**
  - Generic name: the descriptive text in brackets, with strengths and IP/BP/USP removed. If the bracket holds only a dose ("500 mg + 250 IU"), the text outside it is used.
  - Dosage form: 14 groups.
  - Therapeutic class: 14 keyword groups; 80% classified.
- **Failure.** The NSQ result text is matched to 18 categories with a severity, and a record's severity is its worst category. 96.1% are classified.
  - **critical:** DEG/EG contamination, sterility, adulterated, endotoxin (including "BET"), microbial, confirmed fake, failed identity test;
  - **major:** assay (including bare "Content"), dissolution, impurities, particulate matter, uniformity;
  - **minor:** description, disintegration, pH, weight, labelling, moisture.
- **Fakes.** When the firm named on a fake's label told CDSCO it did not make the batch, the record is **not** attributed to that firm (45 records).
- **Buyer named instead of maker.** Rows whose manufacturer field names the supplying public buyer ("Supplied by Kerala Medical Services Corporation") are treated as maker unknown (35 records).
- **Entity resolution.**
  - Units are firm + state; firms are units joined across states.
  - Names are normalised, blocked, scored, and merged at a score of 92 or more; the 80–92 band goes to human review.
  - Rules and evaluation: [ENTITY_RESOLUTION.md](ENTITY_RESOLUTION.md). Merges: `data/staging/entity_matches.csv`.

## The memory's graded response (`dawadrishti/memory.py`)

The first rule that matches wins. The ERP's purchase-order check uses the same rules.

| Level | Response | Rule | In the ERP |
|---|---|---|---|
| 3 | Pause new orders | A critical failure in the last 12 months, or debarred by a buyer | PO blocked unless an override is recorded |
| 2 | Test every batch | A critical failure 13–36 months ago, or 2+ alerts in the last 12 months | Warning; no skip-lot testing |
| 1 | Prefer alternatives | Any alert in the last 36 months | Warning |
| 0 | No recent national record | Nothing in 36 months | Clear (absence of a record, not a certificate) |

**The windows are a [GUESS].**
- **12 months:** close to the 8-month median from a unit's first failure to its next.
- **36 months:** where repeat failures become rare.

They should be set with drug controllers.

**Supply position (reference console).**
- **Concentration:** each supplier's share of the buyer's last 12 months of order quantity for the item, with the Herfindahl index. "Single source" means over 90%; "concentrated" means an index above 0.5.
- **Days of cover:** cleared stock not yet issued, divided by mean daily issues over the last 90 days. It is also shown including stock still in testing.

## Simulated ERP (`dawadrishti/erp/simulate.py`, seed 42)

| Parameter | Value | Basis |
|---|---|---|
| Buyers | 1 national agency + 4 state corporations (**fictional names**) | Mirrors the national (Jan Aushadhi, CMSS) and state (TNMSC, RMSCL…) structure |
| Period | Jan 2025 – Aug 2026; 6,100 procurement cases | [GUESS] |
| Suppliers | 160 **real** manufacturers from the alerts (70 repeat, 90 occasional) + 60 with no national record | Real names and real national records; their orders and debarments here are **simulated** and labelled so in the app |
| Batch failure probability | 2.5% × (1 + 1.2 × the manufacturer's real national alerts in the 12 months before receipt, capped at 5) × dosage-form factor; 0.5× for suppliers with no record | National NSQ rate ~2.7% [SOURCE]; the multiplier is a [GUESS] |
| Failure type of a failed batch | Drawn from that manufacturer's real failure mix | Real |
| Lab turnaround | Gamma, mean 9 / 21 / 14 / 10 / 28 days by buyer; one lab 30% slower | [GUESS] |
| Issue before clearance | Buyer base rate (1–10%) × (1 + turnaround/15) | [GUESS]: the mechanism process mining should find |
| Sample sent uncoded | 0.5–5% by buyer | [GUESS] |
| Payment before clearance | 1–8% by buyer | [GUESS] |
| Debarment | After 2–3 own failures in 12 months, or any critical failure; **lasts 12 months** | [GUESS], in line with tender clauses (Kaysons was banned for one year, then reinstated) |
| National memory (DawaDrishti mode) | At purchase-order time, skip a supplier debarred by **any** buyer or with ≥ 2 national alerts in 12 months, if an alternative is on the rate contract | Design of the system |
| Contract lab-turnaround limit (rule R6) | 21 days | [GUESS] |

**What the simulated data cannot show:** real buyers' behaviour, real lab turnaround, or real conformance. It shows that the process-mining and risk methods work and what they would find.
