# Demo Day — 3-slide deck & script · Team ai-rangers
**Problem statement:** Smart Health — AI-Driven Health Center & Supply Chain Management
**Google Slides file name:** `Smart Health _ ai-rangers`
**Live:** https://smart-health-20737125641.asia-south1.run.app

Guidance from organizers: exactly 3 slides · 3 minutes · non-technical · show what you
built, not jargon. Lead with the solution and its impact.

---

## SLIDE 1 — Problem & Solution
**Title:** Medicines run out before anyone knows

**The problem**
- A district health officer oversees 30+ rural health centres on paper registers and
  phone calls — a medicine stock-out is found only when a patient is turned away.
- No real-time view of stock, staff, beds, or tests across the district.

**Our solution — Smart Health**
- A live district command centre + a 60-second daily-report app for PHC staff,
  with multi-language support.
- The system warns days *before* a centre runs out and tells the officer what to do.

*Visual:* district dashboard screenshot · *Footer:* Live on Google Cloud

---

## SLIDE 2 — Key Features & Innovation
**Title:** Built for the last mile — and hard to cheat

- **Predicts & prevents stock-outs** — flags a shortage days early and auto-suggests
  moving medicine from a surplus centre to one about to run dry.
- **Report any way** — tap, photograph a paper invoice, *speak* it, or *text by SMS*
  from a basic phone. No smartphone or internet needed.
- **Anti-corruption by design** — rejects impossible entries, signs every report to a
  person, and cross-checks with citizens who scan a QR poster at the centre.
- **Early outbreak warning** — spots a spike in fever/diarrhoea medicine across
  neighbouring centres before it spreads.

*Innovation line:* Real algorithms make the decisions; the AI only explains them, in
the officer's own language — so it runs reliably on a ₹1,000 phone.

*Visual:* operator phone app + a "possible misreport" flag.

---

## SLIDE 3 — Impact & Scalability
**Title:** Fewer stock-outs, less diversion, money saved

**Impact (shown live in one demo district)**
- Shortages caught days early → patients not turned away.
- Surplus medicine redistributed instead of emergency-bought → public money saved.
- Every unit of stock signed and cross-checked → diversion becomes easy to catch.

**Ready to scale**
- Already live on Google Cloud — deployable to a real district in weeks.
- Grows with: **a pilot in your constituency's PHCs**, an SMS/WhatsApp gateway for the
  last mile, and integration with **ABDM, e-Aushadhi and HMIS**.

**The ask:** Give us **one block of PHCs for a 90-day pilot** — we'll show the numbers.

*Visual:* all-centres grid (green/amber/red) with the impact figures.

---

## 3-minute speaker script (~430 words)

**[0:00 – 0:35 · Problem]**
"Namaste. Imagine a mother walks two hours to her village health centre for her child's
fever medicine — and it's out of stock. Nobody knew, because across 30-plus rural
centres, a district health officer still tracks everything on paper registers and phone
calls. Stock-outs are discovered only *after* a patient is turned away."

**[0:35 – 1:05 · Solution]**
"We built Smart Health. On one screen, the officer sees every centre live — stock,
staff, beds, tests. And the system warns them *days before* a medicine runs out, in
their own language. The health worker files the whole daily report in about a
minute, from a phone."

**[1:05 – 2:05 · Features — point at the screen / demo]**
"Three things make it real for the ground. One — it doesn't just warn; it acts. It spots
a surplus at one centre and tells the officer to move medicine to the centre about to run
dry. Two — it reaches everyone. A worker with no smartphone can just *send an SMS*, or
*speak* the numbers in their own language — the AI fills the form. Three, and most important for
public money — it's hard to cheat. It rejects impossible entries, signs every report to a
named person, and lets *citizens themselves* confirm from a QR poster whether the doctor
was there and the medicine was in stock. If reports don't match reality, the officer gets
a flag — pointing them exactly where to inspect."

**[2:05 – 2:40 · Impact]**
"The result: shortages caught days early, surplus medicine reused instead of
emergency-bought, and stock that's finally accountable. Fewer patients turned away, public
money saved, and corruption that's easy to catch — by design."

**[2:40 – 3:00 · Scale + ask]**
"It's already live on Google Cloud and can run in a real district in weeks. With your
support, we integrate with ABDM and e-Aushadhi and take it state-wide. Our ask is simple:
give us one block of PHCs for a 90-day pilot, and we'll bring you the numbers. Thank you."

---

## Likely MP questions — quick answers
- **"Does it need internet / smartphones?"** No. It's offline-first, and a worker can
  report by plain SMS from a basic phone; it syncs when the network returns.
- **"How do you stop staff from faking the data?"** Four ways: impossible values are
  rejected, every entry is signed to a person and permanently logged, the system flags
  suspicious patterns for inspection, and citizens independently confirm via QR.
- **"What does it cost?"** It runs on the phones staff already have plus one cloud
  container — very low cost per district; Google Cloud credits cover the pilot.
- **"Patient privacy?"** We store no patient personal data — only stock, staffing and
  coarse availability. The public page shows only "available / low / out".
- **"Will it fit our existing systems?"** Yes — it's built to sync with ABDM,
  e-Aushadhi and HMIS rather than replace them.
- **"Is the AI reliable?"** The decisions are made by transparent algorithms, not the AI.
  The AI only translates and explains — so a bad AI response can never break the system.
