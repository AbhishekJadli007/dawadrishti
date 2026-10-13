# Naming manufacturers: the policy

DawaDrishti names real firms, so how it names them is part of the design. It is a **public-record aggregator with a risk
signal for buyers, not a blacklist.**

1. **Public pages show the record, never a prediction.**
   - The public lookup and the manufacturer page show only what CDSCO published: alert month, product, failure, lab, batch.
   - Predicted scores and ranked lists of named firms appear only in the buyer view.
   - The API enforces this, not just the web page. Public responses from `/api/v1/lookup` and `/api/risk` carry no score and no ranked list.
   - With `DAWADRISHTI_BUYER_KEY` set on the server, the buyer view needs that key, sent as the `X-Buyer-Key` header.
   - The public demo runs without a key, and every buyer response then states "open demo".
2. **Every figure has an as-of date.** Each lookup returns `data_as_of` (the latest alert month loaded) and `generated_at`.
3. **Every page says what the data does not contain:**
   - passing batches, so there is no failure rate;
   - licence actions;
   - patient harm;
   - firm replies and re-tests unless published;
   - state findings never sent to CDSCO;
   - sampling effort.
4. **A correction route.**
   - Every record links to a correction request (`.github/ISSUE_TEMPLATE/correction.md`).
   - Confirmed errors are fixed in the rule that caused them, not patched by hand.
5. **`regulatory_action` is a field, empty by default.** It is filled only from a cited CDSCO or state order, never inferred from alerts.
6. **The language model never characterises a firm.**
   - Questions are answered by fixed query templates that return tables of published records.
   - The model only chooses a template and its filters. It writes no SQL and no prose about any manufacturer.
7. **Rank units, not people, and rank on the record.**
   - Lists rank manufacturing units by published alert counts.
   - Ranked predictions are for deciding where to sample or test, and are worded that way ("where to sample next"), not as findings.
8. **Uncertain identity shows no record.** A name that matches below the automatic-merge threshold (92) returns candidates for a person to confirm. One firm's record is never shown under another firm's name.
9. **Fakes are not counted against the firm whose name they abuse.**
   - Rows where the named firm denied making the batch are excluded (45 rows).
   - Rows that name a supplying public buyer instead of a maker are excluded (35 rows).
10. **Simulated data is labelled where it appears.** Buyer orders and debarments in the reference console are simulated, even though the national record beside them is real.
