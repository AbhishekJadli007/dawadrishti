# Demo video script (about 3 minutes)

Record with QuickTime (File → New Screen Recording) or OBS, at 1440×900 or larger.

**Before you record:**
- Start the app with `uvicorn api.main:app --port 8000`, or use the Hugging Face link.
- Use a fresh browser window at 90% zoom, with the view switch on **Public**.
- If you clicked around earlier, run `python -m dawadrishti build` so the buyer console starts clean.
- Speak slowly. Every number below is on screen when you say it.

---

## 1. The finding: 0:00–0:35 · **Study** tab

**Show:** the headline and the big 64.9%.

> "CDSCO publishes every medicine batch that fails a government lab test. We joined nine years of those alerts, 6,442 failed batches, by manufacturer. Two in three came from a factory that was already on the list. A buyer checking that record before ordering would have seen it. Today no buyer's system reads it."

**Scroll** to the four cards.

> "The next failure comes about eight months after the first. Half the time a different lab, in a different state, catches it."

**Point** at the matching-rule table.

> "This only works if you know which names are the same factory. With exact names it looks like 4%; the same factory is spelled up to 14 ways."

## 2. Honesty: 0:35–0:55 · still on **Study**

**Scroll** to the worked cases.

> "And the disasters? Coldrif and the Gambia syrups had no national alert before the deaths. Kaysons' failures never reached the national list. So the memory must also take state-lab and buyer results. We show that, not hide it."

## 3. The lookup: 0:55–1:35 · **Lookup** tab

1. Click the example **Sresan Pharmaceuticals**. A list of candidates appears, not a record.

   > "A name that doesn't match clearly gets candidates, never a guess. One firm's record is never shown under another's name."

2. Click **Sresan Pharmaceutical Manufacturer · Tamil Nadu**.

   > "Every row is a published alert. There is an as-of date, what this data does not contain, and a way to ask for a correction. No predicted score on a public page."

3. Switch to **Buyer** (top right) and click the example **Nestor Pharmaceuticals**.

   > "A buyer gets a graded response: here, 'test every batch', because of ten alerts in twelve months. The model score is labelled for what it is: the chance of regulatory attention, with its tested accuracy."

## 4. Inside a buyer's ERP: 1:35–2:15 · **Buyers** tab (simulated buyers, real records)

1. Pick **Southern State Corporation** and the item **Bisacodyl · Tablet**. Point at the supply panel.

   > "Before acting, the buyer sees concentration and days of cover."

2. On **Scott-Edil Pharmacia Ltd** ("Test every batch"), click **Raise PO**.
3. In the queue on the right, click **Receive** on the new row and type the batch **2418853T003**.

   > "This exact batch is already on CDSCO's list, so it is held on receipt, before our own lab even tests it."

4. Click **Issue** on any batch still in quarantine.

   > "And nothing can be issued until the lab clears it."

## 5. Can you trust it: 2:15–2:40 · **Quality** tab

> "We checked our PDF parser against CDSCO's own portal: 97% of rows match, and fields agree between 96.7 and 99.8 percent. We labelled hard name pairs and measured the matcher: it never merged two different firms on the held-out pairs. Anything uncertain goes to this review queue."

**Optional (+10 s), Process tab:** scroll to "On a log we did not write".

> "The same conformance engine reads the public BPI 2019 SAP log, 1.6 million events, reproduces its published counts, and finds 655 invoices paid before the goods arrived."

## 6. Models, and closing: 2:40–3:00 · **Models** tab

> "We compare every model with simple rules. Where the simple rule wins, on the top 50, we say so. And it isn't just learning where inspectors look.
> DawaDrishti is open source, with one API any ERP can call. It is a public-record aggregator with a risk signal for buyers, not a blacklist. Next: let state labs and buyers send their results in."

---

**If you have time, a 15-second extra:** on the **Ask** tab, ask "Which antibiotic tablets from Gujarat failed since 2024?" Show the template badge and the filters.

> "The AI only picks a reviewed query. It never writes SQL or anything about a firm."
