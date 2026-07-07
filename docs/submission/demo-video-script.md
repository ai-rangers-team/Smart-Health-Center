# Demo Video — Shot List & Narration Script

Target length: **3:30–4:30** (limit 3–5 min). Record at 1080p, screen capture +
voiceover. Before recording: run `scripts/seed --reset` locally against prod
Firestore, close extra tabs, set browser zoom 100%, use two Chrome profiles
(admin: rishimishra1508@gmail.com · operator: rishi.mishra@wonderlendhubs.com).
Have the app open in **Marathi** on the operator profile and **English** on admin —
the language contrast lands the inclusivity point without narration.

> Timings are cumulative targets. If running long, cut Scene 6 (bulk upload)
> first — the wow features are Scenes 3–5.

---

### Scene 1 — The problem (0:00–0:30)
**Visual:** Title slide from the pitch deck (problem slide), then cut to the live
dashboard URL being typed.
**Narration:**
"A district health official in rural India oversees thirty or more primary
health centres — with paper registers and phone calls. Medicine stock-outs are
discovered only when a patient is turned away. We built Smart Health: a
real-time command centre for the district, and a sixty-second daily report app
for the health centre operator. This is running live on Google Cloud Run."

### Scene 2 — District dashboard (0:30–1:15)
**Visual:** Admin profile, dashboard fully loaded. Slow scroll: AI briefing
typing itself out, impact line, alerts panel, centre grid with status colours.
Hover one critical centre card.
**Narration:**
"This is the district command centre. The morning briefing is written by
Gemini — in the official's own language — from live data. Below it, every
alert is deterministic: recency-weighted forecasting predicts each medicine's
stock-out date at every centre. Pashan is critical — out of stock in two days.
The performance score blends attendance, footfall, stock and diagnostics, so
underperforming centres are flagged automatically, with an AI explanation of
why."

### Scene 3 — Operator daily report + invoice OCR (1:15–2:30)
**Visual:** Switch to operator profile (Marathi UI). Log today's footfall with
the stepper. Then tap **Scan restock invoice**, pick the sample invoice photo,
show extracted quantities pre-filling the stock form, adjust one value, Save.
**Narration:**
"Now the other side — a PHC operator in Mulshi, on a phone, in Marathi. The
whole daily report takes under a minute: patients seen, staff present, beds,
stock. And when the medicine delivery arrives, they don't type at all — they
photograph the invoice. Gemini reads it, matches items to this centre's own
catalog, and pre-fills the quantities. The operator reviews and saves — AI
proposes, a human confirms, and only then does the write happen."

### Scene 4 — Real-time recompute (2:30–3:00)
**Visual:** Split/side-by-side or quick cut: the moment operator saves stock,
the admin dashboard card updates (status colour, days-remaining, alert
appears/resolves) with NO refresh.
**Narration:**
"Watch the district side — no refresh. The save recomputed the forecast, the
score and the alerts, and Firestore pushed it live in about a second. The
official sees the district as it is right now, not as it was last month."

### Scene 5 — Redistribution + multilingual AI (3:00–3:45)
**Visual:** Admin clicks **Generate recommendations**. Recommendation appears
with typewriter effect: transfer paracetamol from surplus centre to deficit
centre, with Gemini's one-line rationale. Then flip language to Hindi — the
briefing regenerates in Hindi.
**Narration:**
"Before a stock-out ever happens, the redistribution engine matches surplus
to deficit across the district — this transfer prevents next week's stock-out
at no procurement cost. And everything the AI writes follows the user's
language. The algorithms decide; Gemini explains."

### Scene 6 — Scale story (3:45–4:10)
**Visual:** Onboard-centre page: the one "expected patients per day" question,
then the bulk CSV upload with the template download.
**Narration:**
"Onboarding is built for scale: a new centre gets safe stock thresholds from
one question a district admin can actually answer, and an entire district — 
thirty or forty centres — onboards from one CSV. The same model rolls up from
district to state."

### Scene 7 — Close (4:10–4:30)
**Visual:** Pitch deck closing slide: architecture strip, live URL, repo QR.
**Narration:**
"FastAPI on Cloud Run, Firestore, Firebase Auth, Gemini 2.5 Flash — deployed
by CI/CD with keyless Workload Identity, covered by sixty tests, live today.
Smart Health, by team ai-rangers: rural healthcare that runs on data instead
of paperwork."

---

## Recording checklist
- [ ] `scripts/seed --reset` run, dashboard shows the 6-centre Pune Rural scenario
- [ ] Sample invoice photo on the phone/desktop for Scene 3 (docs/submission/assets — add one)
- [ ] Gemini quota fresh (standby API key ready; avoid rehearsing briefings on the prod key)
- [ ] One full timed rehearsal < 5:00
- [ ] Export ≤ 1080p MP4; audio clear, no background noise
