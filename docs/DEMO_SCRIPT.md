# Demo video script (about 3 minutes)

Record with QuickTime (File → New Screen Recording) or OBS, at 1440×900 or larger.

**Before you record:**
- Open the live link once a minute early, because the free server sleeps.
- Use a fresh browser window at 100% zoom.
- Speak slowly. Every number below is on screen when you say it.

The app has four sections, in the top bar (or the bottom bar on a phone): **Home**, **Check a manufacturer**, **For buyers** and **How we know**.

---

## 1. The finding: 0:00–0:35 · **Home**

**Show:** the headline. Wait for the red ring to fill to 64.9%.

> "India publishes every medicine batch that fails a government test. We joined nine years of those alerts, about 6,400 failed batches, by factory. Two in three came from a factory that was already on the list. A buyer checking that record before ordering would have seen it. Today nobody does."

**Scroll** slowly through "How it works" and the four numbers.

> "The next failure comes about eight months after the first, and half the time a different lab, in a different state, catches it."

**Pause** on the bar comparison.

> "This only works if you know which names are the same factory. With exact names it looks like 4%. The same factory is spelled up to 14 ways."

## 2. Honesty: 0:35–0:55 · still on **Home**

**Scroll** to "The disasters, checked against the record".

> "And the disasters? Coldrif and the Gambia syrups had no national alert before the deaths. Kaysons' failures never reached the national list. So the memory must also take results from state labs and buyers. We show that, not hide it."

## 3. Check a manufacturer: 0:55–1:35 · **Check a manufacturer**

1. Click the example **Sresan Pharmaceuticals**. A "Which factory did you mean?" list appears.

   > "When a name isn't clear, it never guesses. You pick the factory, so no one's record appears under the wrong name."

2. Click **Sresan Pharmaceutical Manufacturer · Tamil Nadu**.

   > "Every published failure, in plain language, with dates, labs and batch numbers. It says what the data can't tell you, and anyone can ask for a correction. No prediction on the public page."

3. Click the example **Nestor Pharmaceuticals**, then switch to **Buyer view**.

   > "A buyer gets a clear answer: 'test every batch', because of ten failures in the last year. The model's risk estimate is labelled for what it is, with its tested accuracy."

## 4. Inside a buyer's system: 1:35–2:20 · **For buyers** (simulated buyers, real records)

1. Click **Use the demo order**.

   > "Before ordering, the buyer sees how concentrated their supply is."

2. On **Scott-Edil Pharmacia Ltd** ("Test every batch"), click **Order from this supplier**.
3. Click the red chip **Try a batch from the national failure list**, then **Receive the delivery**.

   > "This exact batch already failed a government test, so it's held on arrival, before the buyer's own lab even sees it."

4. Click **Next: release**, then **Release to hospitals**. The button shakes, and the system says no.

   > "And nothing can reach a hospital until the lab clears it. Every step lands in this event log, which our process mining reads."

## 5. Can you trust it: 2:20–2:45 · **How we know**

Click **Data quality**.

> "We checked our PDF reader against CDSCO's own portal: 97% of rows match, and fields agree between 96.7 and 99.8 percent. We tested the name matching on hand-labelled pairs: it never merged two different firms. Anything uncertain goes to a review queue."

Click **Process checks** and scroll to "On a log we did not write".

> "The same rule engine reads a real SAP purchasing log of 1.6 million events, reproduces its published counts, and finds 655 invoices paid before the goods arrived."

## 6. Close: 2:45–3:00 · **Home**

> "DawaDrishti is open source, with one API that any buyer's system can call. It's a public-record aggregator with a risk signal for buyers, not a blacklist. Next: let state labs and buyers send their results in."

---

**If you have time, a 15-second extra:** in **How we know → Ask the data**, type "fake cough syrups found in 2025". Show the template and filters it chose.

> "The AI only picks a reviewed query. It never writes SQL or anything about a firm."
