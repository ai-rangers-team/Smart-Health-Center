# Submission Kit — Build with AI: Code for Communities

Deadline: **July 8, 2026, 11:59 PM IST** · Track 3: Smart Health — AI-Driven
Health Center & Supply Chain Management · Team **ai-rangers**

## What goes where on the hack2skill form

| Form field | Use | Status |
|---|---|---|
| Working solution URL | https://smart-health-20737125641.asia-south1.run.app | Live, verified |
| GitHub repository | https://github.com/ai-rangers-team/Smart-Health-Center | **Must be made PUBLIC before submitting** |
| Explain your solution (≤1,000 chars) | Paste `solution-explanation.txt` (944 chars) | Ready |
| Presentation PDF (≤5 MB) | Upload `Smart-Health-Pitch-Deck.pdf` (11 slides, 1.1 MB) | Ready |
| Technologies used (≤1,024 chars) | Paste `technologies-used.txt` (968 chars) | Ready |

## Files in this folder

- `Smart-Health-Pitch-Deck.pdf` — the submission deck (generated from `pitch-deck.html`)
- `Smart-Health-Pitch-Deck.pptx` — editable copy of the same deck for the team
- `pitch-deck.html` — deck source; regenerate the PDF with:
  `chromium --headless=new --no-pdf-header-footer --print-to-pdf=Smart-Health-Pitch-Deck.pdf pitch-deck.html`
- `solution-explanation.txt` / `technologies-used.txt` — form texts (within char limits)
- `demo-video-script.md` — 3–5 min shot list + narration for the backup demo video
- `assets/` — product screenshots used by the deck

## Before submitting (owner: team)

1. Make the repo public: `gh repo edit ai-rangers-team/Smart-Health-Center --visibility public`
   (also remove any leftover branch protection surprises after flipping).
2. Record the demo video per `demo-video-script.md` (reset demo data first:
   `cd api && PYTHONPATH=. ../.venv/bin/python -m scripts.seed --reset`).
3. Keep a standby Gemini API key ready (free-tier daily quota) — swap via the
   `GEMINI_API_KEY` GitHub secret if the primary exhausts on demo day.
4. One timed rehearsal of the live demo (< 5 min) on the production URL.
