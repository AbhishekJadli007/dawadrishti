# Contributing

```bash
python3.11 -m venv .venv && source .venv/bin/activate && pip install -r requirements-dev.txt
pytest && python -m dawadrishti build
```

**Rules:**
- Never present simulated data as real.
- Follow [docs/NAMING_POLICY.md](docs/NAMING_POLICY.md): public pages show records, never predicted scores; no model writes text about a firm.
- Entity-resolution changes are tuned on the dev pairs and reported on a test set that was not used to tune them.
- New parameters go in `docs/ASSUMPTIONS.md` with a source or the word guess.
- Every model change is compared with its baselines in `docs/EVALUATION.md`.

**Where help is most useful:**
- Reviewing the 200 entity-resolution labels (`data/er/labelled_pairs.csv`) and the review queue on the Quality page.
- More purchase-to-pay and quality rules for the conformance engine, checked on BPI Challenge 2019 and on real buyer logs.
- A contribution route for state-lab and buyer test results (the Kaysons gap).
- Better product and therapeutic-class mapping (WHO ATC, NLEM).
- A DVDMS / e-Aushadhi connector that calls `/api/v1/lookup` at PO and goods-receipt time.
- A Hindi interface.
