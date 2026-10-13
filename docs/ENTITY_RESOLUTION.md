# Entity resolution: which names are the same factory?

**Why it matters.**
- The headline study asks whether a failing batch's maker was already on the national record. That question depends entirely on knowing which alert rows name the same factory.
- With exact name strings, only **4.2%** of failed batches look like repeats, because one factory is written up to 14 different ways.
- With the resolution below, the figure is **64.9%**.

Code: `dawadrishti/etl/clean.py` (`name_key`), `dawadrishti/etl/entities.py` (matching), `dawadrishti/entity_eval.py` (evaluation).
Labels: `data/er/labelled_pairs.csv`. Output: `artifacts/entity_resolution.json`, shown in the app under **How we know → Data quality**.

## The decision: unit, then firm

| Level | ID | Definition | Why |
|---|---|---|---|
| **Unit** | `manufacturer_id` (M…) | Firm name + state of the manufacturing address | State drug controllers license each manufacturing site, so this is the level a regulator acts on. The memory keys on it. |
| **Firm** | `firm_id` (F…) | Units joined across states when the names match | A buyer's rate contract is with the firm. Profiles roll units up to the firm and say so ("other units of this firm on record"). |

The state of a unit comes from its address. When that extraction is wrong, one unit can split in two; see the errors below.

## Normalisation rules (v2)

Each rule was added for an error found in the development pairs.

| Rule | The error it fixes |
|---|---|
| Drop prefixes such as "Mfg By:" and "M/s." | 42 rows began with "Mfg By:", so they never reached the right block |
| Drop the legal form: Pvt Ltd, Private Ltd, (P) Ltd, Limited, LLP, Inc | v1 left "Private Ltd" and "Pvt..Ltd" in the name |
| Treat "(I)", "(India)" and "India" as nothing | "Salud Care (I)" vs "Salud Care (India)" |
| Map "Pharmaceuticals" and its misspellings to "pharma" | "Pharmaceticals", "Pharnaceuticals", "Pharmaceutica ls" |
| Map lab, healthcare, life sciences, bio sciences, biotech, formulation, industries to one form each | "Life Sciences" vs "Lifesciences", "Helathcare" |
| Drop address residue at the end of a name: "No", "K. No", "Unit-II" | The name/address split sometimes leaves a plot-number word |
| Compare names with spaces removed | "NitinLifesciences", "J.M.Laboratories", "CyanoPharma" |

**Matching steps:**
1. **Block** on the first 4 characters of the name with spaces removed.
2. **Score** each pair inside a block: 100 if the space-free names are equal, otherwise RapidFuzz token-sort ratio.
3. **Union** every pair scoring at least **92**. Units match only within a state; firms join units across states.

## Labelled pairs

How the pairs were drawn:
- **Development set (120 pairs).** Sampled from the v1 blocking: 30 pairs with identical keys, 50 pairs scoring 85+ with different keys, 40 pairs scoring 70–85. I used this set to find normalisation errors and to choose the threshold.
- **Test set (80 pairs).** Drawn after the v2 fixes from the v2 blocking. It leaves out the dev pairs and pairs with identical text. It is stratified: 10 with equal keys, 25 scoring 92+, 25 scoring 85–92 and 20 scoring 75–85. The order was shuffled, and the pairs were labelled **with scores hidden**. It is used once, for the numbers below.

How the pairs were labelled:
- **Label:** "same firm?", judged from the names and addresses.
- **Labeller:** the AI assistant. 16 labels are marked unsure, and **every label awaits human review.**
- **Caution:** both sets oversample the hard score band. The numbers are precision and recall on *difficult* pairs, not on all pairs.

## Results (test set, firm level)

| Matcher | Precision | Recall | F1 | Unit-level recall |
|---|---|---|---|---|
| Exact name | 1.00 | 0.00 | 0.00 | 0.00 |
| Normalised name, v1 rules | 1.00 | 0.13 | 0.22 | 0.12 |
| Fuzzy ≥92, v1 rules (before the fixes) | 1.00 | 0.48 | 0.65 | 0.41 |
| Normalised name, v2 rules | 1.00 | 0.18 | 0.30 | 0.18 |
| **Fuzzy ≥92, v2 rules (in use)** | **1.00** | **0.63** | **0.77** | **0.57** |
| Fuzzy ≥92, v2 + distinctive-word check (tried, rejected) | 1.00 | 0.48 | 0.65 | 0.45 |

**Threshold sweep, v2 rules (precision / recall):**

| Threshold | Dev | Test |
|---|---|---|
| 80 | 0.87 / 1.00 | 0.80 / 0.98 |
| 86 | 0.96 / 0.97 | 0.96 / 0.89 |
| 90 | 0.98 / 0.96 | 1.00 / 0.80 |
| **92** | **0.99 / 0.95** | **1.00 / 0.63** |
| 96 | 1.00 / 0.85 | 1.00 / 0.39 |

**Why 92.**
- On the dev set, 90 and 92 tie on F1 (0.97). We took the higher-precision one.
- A false merge would put one firm's failures on another firm's record, which is the worst error this system can make. A missed merge only splits one firm's history in two.
- The test set shows that 92 gives up recall on the hardest pairs. That is why the 80–92 band goes to people instead of being decided automatically.

**With human review.** If reviewers confirm the true matches in the 80–92 band, firm-level recall on the test set rises to **0.98**. Of the 34 test pairs in that band, 20 are true matches and 14 are not, so the band needs a person and cannot be merged automatically.

**What the 21 test errors are (all missed merges, no false merges):**
- typos inside generic words: "Lifescienses", "Durgs", "Pharmacls", "Heatlhcare", "lnjectables" (a lower-case l read for a capital I);
- place names left at the end of a name: "Marc Lifesciences Sikkim", "Konis Pharmaceuticals Krishna", "Mayasha Lifesciences H.B";
- address text left in the name: "Legend Industries, Unit-II, Plot No. C1/200…";
- single-letter typos in short names: "Morepan" vs "Morepen", "Standord" vs "Stanford".

These become v3 rules only after a fresh labelled set exists. Fixing them on this test set would turn it into a development set.

## Population (all alerts with a known maker)

| Measure | Value |
|---|---|
| Rows | 6,557 |
| Distinct manufacturer strings, with address | 5,521 |
| Distinct names after the name/address split | 2,648 |
| Units after resolution | 1,994 |
| Firms (units joined across states) | 1,797 |
| Units written more than one way | 485 (up to 14 spellings) |
| Firms with units in more than one state | 154 |

## Review queue

- **What is in it.** **How we know → Data quality** lists 206 pairs scoring 80 to <100 within a block:
  - 103 that were merged automatically (score 92–99), to be checked;
  - 103 that were not merged (score 80–91), which need a decision.
- **Order.** The pairs that move the most alerts come first.
- **Recording decisions.** Reviewers mark each pair "same" or "different", export the decisions, and save the file as `data/er/decisions.json`.
- **Applying them.** The next `python -m dawadrishti build` applies them:
  - "same" joins the two names even below the threshold: as one unit if they are in the same state, as one firm otherwise;
  - "different" stops that pair from being merged directly.
  - The queue then shows each decided pair as "reviewer: same" or "reviewer: different".

## Effect on the headline

- **Missed merges** split one factory into two. Each part then has fewer earlier failures, which **lowers** the repeat share.
- **False merges** raise it.
- **Net effect.** On the test pairs the matcher made no false merges and missed about a third, so the headline 64.9% is, if anything, **conservative**.
- **Across matching rules.** The study recomputes every number under five matching rules (see **How we know → The study**). Every rule above exact strings gives 62.8%–67.8%.

## Reviewing the labels

```bash
python -m dawadrishti.entity_eval --review        # all 200 pairs; or --review test for the 80 test pairs only
python -m dawadrishti.entity_eval                 # re-score with your labels
```

**How the review works:**
- The tool shows each pair's names, states and addresses, but **not** the assistant's label, and asks "same firm? y/n".
- Answers are saved to `human_label` in `data/er/labelled_pairs.csv` after each pair, so you can stop at any time and resume.

**How the scores change:** the evaluation uses the person's label wherever there is one, and reports how often the assistant agreed.

## Next

1. Human review of all 200 labels (above), and a fresh test set of 100+ pairs labelled by two people, with agreement reported.
2. v3 rules for the error types above, evaluated on that fresh set.
3. Optional adjudication of the 80–92 band by Gemini, scored against the human labels before it is trusted.
