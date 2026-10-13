---
name: Correction request
about: Ask for a record to be corrected or annotated (wrong firm, wrong state, a re-test result, a firm reply)
title: "Correction: <manufacturer name>"
labels: correction
---

**Which record?** Manufacturer name and unit id as shown on the lookup page (e.g. M00008), alert month and batch number.

**What is wrong?** (wrong firm or merged with another firm / wrong state / wrong failure type / missing re-test or reply / other)

**Evidence.** A link to the CDSCO alert, a state or court order, a re-test certificate, or the firm's published reply.
Do not attach personal data.

**Who is asking?** (the firm, a buyer, a regulator, a member of the public)

Each request is checked against the published alert. A confirmed error is fixed at the source rule (cleaning, entity
resolution) so it does not come back in the next build, and the change is noted in the release notes.
