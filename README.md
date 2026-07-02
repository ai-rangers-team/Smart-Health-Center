# Smart-Health-Center

Multilingual, real-time district health-centre management platform. PHC operators enter stock/beds/footfall/attendance/tests; the system forecasts stock-outs, scores underperformance, recommends redistribution, and surfaces it live to a district admin with AI-written explanations.

See `Implementation Plan.md` for the full build plan.

## Architecture

Single Cloud Run container. FastAPI serves the REST API and the built React static files. Firestore is the real-time operational store. Firebase Auth (Google Sign-In) with custom claims for roles. Gemini 2.5 Flash is the communication layer only — real algorithms make the decisions.

## Repo layout

```
smart-health/
├── api/    # FastAPI backend
└── web/    # React frontend (Vite)
```

## Backend — local dev

```bash
cd smart-health/api
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in GEMINI_API_KEY, FIREBASE_CREDENTIALS_PATH
pytest -q
uvicorn app.main:app --reload
```
