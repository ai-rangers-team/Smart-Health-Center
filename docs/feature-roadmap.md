# Smart Health — Feature Exploration & Roadmap

*How would a large product organization design this platform? Feature landscape
by persona, benchmarked against enterprise ops consoles (ServiceNow, Salesforce
Health Cloud, Datadog) and Indian public-health systems (e-Aushadhi, DHIS2,
CommCare). Drafted before ground-visit research — field insights override this.*

Legend: ★ = differentiator (demo-worthy) · ⚙ = pilot-required plumbing · 📅 = scale/later

---

## 1 · Health Worker (PHC operator)

The MNC lens: *reduce effort to zero, then add pride.* Consumer-grade UX for a
non-consumer context.

| # | Feature | Why it wins | Tag |
|---|---|---|---|
| H1 | **Batch & expiry tracking** — record batch no. + expiry on restock (invoice OCR already reads them!); "expiring in 30/60/90 days" list; FEFO hint ("issue the old strip first"); expiry alerts feed redistribution ("move it before it dies on the shelf") | Expired-stock write-offs are one of the biggest real losses in PHC supply chains; e-Aushadhi's core value is exactly this. We already *capture* the data on invoices and throw it away | ★ |
| H2 | **Report reminders** — if no daily report by ~11 AM, a gentle nudge (push/SMS/WhatsApp); DHO sees who was nudged | Compliance is the #1 data-quality lever; nudges beat memos | ⚙ |
| H3 | **My-centre pride view** — reporting streak, "22 days in a row", monthly summary of their own centre, small milestones | Gamified compliance (Duolingo-style); operators are people — recognition is free and drives retention of the habit | ★ |
| H4 | **Emergency stock request button** — one tap: "urgent: need X" → creates a district task + alert; distinct from routine forecast alerts | Today the operator's only voice is the daily report; give them a pull cord | ★ |
| H5 | **Referral note** — "sent patient to CHC/District Hospital" (count + reason category, no PII) | Closes the loop between centres; referral volume is a health-system signal DHOs act on | 📅 |
| H6 | **Offline write queue** — reports queue locally, auto-sync when network returns (finish the PWA story we already tell) | We claim it on stage; it must become true | ⚙ |
| H7 | **IVR / missed-call reporting** — operator gives a missed call, gets an IVR call-back in their language, speaks the numbers | The last 10% of the last mile: works on a ₹500 feature phone with zero literacy assumptions | 📅 |
| H8 | **In-app help videos** — 60-second in-language clips per screen | Cuts training cost for district rollouts; a rollout blocker otherwise | ⚙ |

## 2 · District Health Officer

The MNC lens: *from dashboard to workflow.* Seeing a problem is step one; the
platform should carry the problem to resolution and remember who owned it.

| # | Feature | Why it wins | Tag |
|---|---|---|---|
| D1 | **Alert workflows (mini-ServiceNow)** — assign an alert to a person, add a note, set status (open → assigned → in progress → resolved), full history; unassigned criticals **auto-escalate** after N hours | Today alerts are see-and-resolve; real districts run on accountability chains. This single feature converts a dashboard into an operations system | ★ |
| D2 | **District map view** — centres as colored pins (status) on the district map; click-through to centre | The single most legible artefact for officials & MPs; instantly fills the "empty real estate"; offline-friendly with self-hosted tiles | ★ |
| D3 | **Trends & benchmarking** — month-over-month per centre, centre-vs-centre ranking, seasonal overlays (ORS in monsoon), district trajectory | Turns snapshots into stories; DHIS2's whole reason to exist. We have the history already | ★ |
| D4 | **Monthly review pack** — one click: auto-generated agenda for the district's monthly review meeting (worst compliance, open flags, wins), printable | The monthly review meeting is a real ritual in Indian health admin; walking in with the pack pre-made is a genuine "life easier" moment | ★ |
| D5 | **Broadcast to operators** — announcement to all/selected centres (in-app + SMS): "polio drive Monday", "submit indent by Friday" | Every district WhatsApp group is this, minus accountability; bring it in-platform with read receipts | ⚙ |
| D6 | **Indent planning (procurement)** — quarterly consumption forecast → suggested indent quantities per medicine, exportable in e-Aushadhi-compatible format | Bridges our forecasting to the actual procurement workflow — the moment we become part of the money loop, we're indispensable | ★ |
| D7 | **Inspection notes** — DHO visit log per centre (date, note, optional photo), shows on centre detail | Pairs with integrity flags: flag → inspect → record outcome; completes the anti-fraud loop | ⚙ |
| D8 | **Staffing & vacancy view** — chronic attendance gaps roll up into a vacancy/absenteeism report per centre | Attendance data exists; this reframes it from "today" to "systemic" | 📅 |

## 3 · Super Admin

The MNC lens: *the platform team's platform.* Rollout control, data governance,
and self-service configuration.

| # | Feature | Why it wins | Tag |
|---|---|---|---|
| S1 | **Catalog templates / state EDL** — define a medicine template once (e.g., "AP PHC Essential Drug List"), apply to all centres of a district in one click; new centres inherit automatically | Nobody manages 100 medicines × 40 centres one by one; templates are how real systems onboard a district in an afternoon | ★ |
| S2 | **Notification routing** — matrix of who gets which alert type over which channel (in-app / SMS / email), per role and district | The difference between "alerts exist" and "alerts reach people at 7 AM" | ⚙ |
| S3 | **Usage analytics** — daily/weekly active users per role, feature adoption, report-submission hour histogram, API error rate (wire Cloud Monitoring in) | You manage what you measure; also the pilot's own success evidence | ⚙ |
| S4 | **Scheduled reports** — weekly district report auto-emailed as PDF to configured officials | Officials live in email/WhatsApp, not in dashboards; push beats pull for adoption above the district | ★ |
| S5 | **Feature flags per district** — enable/disable features (voice, citizen QR, outbreak) per district from the console | Staged rollouts are how enterprises de-risk; also lets one deployment serve districts with different maturity | 📅 |
| S6 | **Data export & retention console** — full district export (CSV/JSON), retention policy settings; DPDP-compliance posture | Government data governance question #1 in any procurement meeting: "how do we get our data out?" | ⚙ |
| S7 | **Translation manager** — edit UI strings per language from the console (no redeploy); flag machine-translated strings for native review | 283 strings × N languages now; a state rollout adds languages faster than deploys should gate | 📅 |
| S8 | **Sandbox / training mode** — a demo district with fake data, resettable from the console, for training sessions | Every enterprise rollout has a training environment; ours is currently "the production seed script" | ⚙ |

## 4 · Cross-cutting platform features

| # | Feature | Why | Tag |
|---|---|---|---|
| X1 | **"Ask the district" AI assistant** — natural-language Q&A over live data ("which centres ran out of ORS last month?", "compare Mulshi and Haveli attendance"), powered by Gemini function-calling over our read APIs, answers in the user's language | The 2026 MNC flagship feature; we have clean structured data + an AI story judges already love. Guardrail: read-only tools, always shows the underlying numbers | ★ |
| X2 | **Notifications hub** — bell icon + per-user inbox (assigned alerts, broadcasts, nudges) | Prerequisite plumbing for D1/D5/H2; standard platform furniture | ⚙ |
| X3 | **Global search** — one box: centres, medicines, users, alerts | Standard enterprise furniture; cheap with our data volume | 📅 |
| X4 | **State level (state_admin role)** — districts-as-cards rollup dashboard, state report | We literally pitch "rolls up from district to state"; one MP meeting away from being asked for it live | ★ |
| X5 | **Accessibility / GIGW compliance** — WCAG AA pass, font-size toggle, screen-reader labels | Government of India web guidelines (GIGW) are a procurement checkbox — and the right thing | ⚙ |
| X6 | **Uptime/status page** — public status.smarthealth.in | Trust artefact for officials; trivial with Cloud Monitoring | 📅 |

---

## Recommended build order (pre-ground-visit)

**Wave 1 — demo differentiators (before the MP meeting):**
1. **D2 map view** — biggest visual upgrade per hour of work
2. **D1 alert workflows** (assign/notes/escalate) — dashboard → operations system
3. **H1 batch & expiry** — deepest real-world supply-chain value, reuses invoice OCR
4. **X1 "Ask the district"** — the AI flagship, unmatched in demos
5. **S1 catalog templates** — makes district onboarding a real story

**Wave 2 — pilot plumbing (with SMS gateway + auth work):**
H2 nudges · X2 notifications hub · D5 broadcast · S2 routing · H6 offline queue ·
S3 usage analytics · H8 help videos · S8 sandbox mode

**Wave 3 — scale story:** X4 state level · D6 indent planning · S4 scheduled
reports · H7 IVR · S5 flags · S7 translation manager

*Ground-visit note: validate H1–H4 and D1/D4 with real operators and the DHO
before building Wave 2 — the field will reorder this list, and it should.*
