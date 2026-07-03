# Smart Health Centre Management — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a multilingual, real-time district health-centre management platform — PHC operators enter stock/beds/footfall/attendance/tests; the system forecasts stock-outs, scores underperformance, recommends redistribution, and surfaces it all live to a district admin with AI-written explanations.

**Architecture:** Single Cloud Run container. FastAPI serves the REST API and the built React static files. Firestore is the real-time operational store (React reads via `onSnapshot`). Firebase Auth (Google Sign-In) with custom claims for roles. Gemini 2.5 Flash is the communication layer only — it never gates a write path. Real algorithms (EWMA forecasting, weighted scoring, greedy redistribution) make the decisions.

**Tech Stack:** Python 3.11 · FastAPI · Firebase Admin SDK (Firestore + Auth) · google-generativeai (Gemini) · slowapi · Pydantic v2 · pytest · React 18 (Vite) · TailwindCSS · Recharts · Firebase JS SDK · Docker · Cloud Run.

## Global Constraints

- **Google Cloud is mandatory** — Firestore, Firebase Auth, Cloud Run, Gemini all count.
- **Gemini model:** `gemini-2.5-flash`, referenced ONLY via the `GEMINI_MODEL` config constant. Gemini 1.5/2.0 are shut down (HTTP 404). Verify the live model id on Day 0 with ListModels before writing AI code.
- **Gemini is never on the live operator-write path.** Alerts on write are deterministic templates. Gemini enriches lazily/separately.
- **Roles** are `district_admin` and `phc_operator`, carried as Firebase custom claims (`role`, `district_id`, `centre_id`) — read by both FastAPI (from the ID token) and Firestore Security Rules (`request.auth.token.*`). No per-request `/users` lookup for authz.
- **Secrets** (Gemini API key, Firebase service-account JSON) come from environment variables only — never committed. `.env.example` documents every key.
- **Languages:** English, Hindi, Marathi (EN/HI/MR). Marathi is the default for the Pune demo. Static translation dict; no Translation API.
- **Response envelope:** success `{ "success": true, "data": {...}, "timestamp": "<iso>" }`; error `{ "success": false, "error": "<msg>", "code": <int> }`.
- **Deadline:** July 8, 2026 23:59 IST. Feature freeze July 6 EOD.
- **Demo district:** "Pune Rural District", 1 CHC + 5 PHCs (Mulshi, Haveli, Ambegaon, Velhe, Bhor + Pune Rural CHC).

## Repository & File Structure

Monorepo, two apps + infra at root.

```
smart-health/
├── api/                              # FastAPI backend
│   ├── app/
│   │   ├── main.py                   # app factory: CORS, slowapi, routers, static mount
│   │   ├── config.py                 # Settings (env), GEMINI_MODEL, SEED_ENABLED
│   │   ├── deps.py                   # verify_token dependency, role guards
│   │   ├── firestore_client.py       # firebase-admin init + db handle + helpers
│   │   ├── routers/
│   │   │   ├── dashboard.py          # district overview + alerts
│   │   │   ├── centres.py            # read: centre, stock, beds, attendance, footfall, tests
│   │   │   ├── operator.py           # write: stock/beds/footfall/attendance/tests (+recompute)
│   │   │   ├── alerts.py             # resolve
│   │   │   ├── ai.py                  # forecast, briefing, redistribution, explain
│   │   │   └── seed.py               # env+admin gated demo loader/reset
│   │   ├── services/
│   │   │   ├── forecasting.py        # ewma, forecast_stockout, forecast_footfall
│   │   │   ├── scoring.py            # compute_performance_score
│   │   │   ├── redistribution.py     # compute_redistribution
│   │   │   ├── alerting.py           # regenerate_alerts (templates, Gemini-free)
│   │   │   ├── recompute.py          # recompute_centre (ties forecasting+scoring+alerting)
│   │   │   └── gemini.py             # Gemini client + prompt templates + 4 enrich fns
│   │   ├── models/
│   │   │   └── schemas.py            # Pydantic request/response models + envelope
│   │   └── seed/
│   │       └── demo_data.py          # Pune Rural District generator + account provisioning
│   ├── tests/
│   │   ├── test_forecasting.py
│   │   ├── test_scoring.py
│   │   ├── test_redistribution.py
│   │   ├── test_alerting.py
│   │   ├── test_auth.py
│   │   └── test_endpoints.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── web/                              # React frontend (Vite)
│   ├── src/
│   │   ├── main.jsx, App.jsx
│   │   ├── firebase.js               # Firebase app + auth + firestore (+offline persistence)
│   │   ├── api.js                    # axios instance + token interceptor + envelope unwrap
│   │   ├── i18n/translations.js      # EN/HI/MR dict + LanguageContext
│   │   ├── hooks/{useAuth.js,useFirestore.js}
│   │   ├── pages/{Login,Dashboard,CentreDetail,MyCentre,NotProvisioned}.jsx
│   │   └── components/…              # generated via Claude Design against the data contract
│   ├── package.json
│   └── .env.example
├── firestore.rules                   # role-scoped security rules
├── firestore.indexes.json            # composite index for alerts query
└── README.md
```

**Parallelization:** Within each phase, tasks are grouped by owner (BE = backend core, AI = forecasting/Gemini, FE = frontend, IN = infra). Tasks in different groups within a phase can run concurrently once their listed dependencies are met.

## Progress Notes (updated July 3, evening)

Checkboxes reflect ATTESTED work only — a step stays unchecked if it could not
be verified yet, even when the code is written. Current state:

- **CREDS LANDED — backend fully built and live-verified.** With the service
  account at `api/secrets/` (git-ignored): Firestore round-trip OK; full demo
  district seeded into live Firestore (`python -m scripts.seed [--reset]`);
  all AI endpoints verified against live Gemini; operator writes + recompute +
  alert regeneration verified end-to-end (`python -m scripts.live_verify`,
  18/18 checks incl. 401/403 claim guards and the wow-path: stock 120→80 →
  fresh critical alert at 2.0 days). Firebase WEB config fetched via the
  Management API and written to `web/.env` + `.env.example` (the web apiKey is
  public-by-design). Tasks 1.4/2.1/2.4/2.5 are now DONE (built by AI lane —
  Devik to review rather than rebuild).
- **Remaining unchecked verify steps are browser-level only:** Google sign-in
  popup (0.4/1.7), live `onSnapshot` in the UI (1.8/2.8), two-tab UI wow-path
  (3.2), plus integration pass 3.4 and Phases 4–5. Backend halves are proven.
  Team accounts get role claims only AFTER first sign-in — sign in once on the
  real frontend, then re-run `python -m scripts.seed`. Confirm the Google
  provider is enabled in Firebase Console → Authentication (ISHA).
- **Read routes (1.5/2.6) now EXIST** (Devik built them before seeing the
  earlier deviation note; merged July 3). The frontend still reads Firestore
  directly via `onSnapshot` (real-time) — the REST reads are optional API
  surface for non-Firestore clients / curl demos. Merge kept the live-verified
  recompute/operator/seed/alerting; took Devik's PEP 562 lazy firestore_client,
  lazy gemini client, redistribution self-transfer fix, centres+dashboard
  routes, expanded tests. Merged suite: 44 tests green, live_verify 18/18
  re-run post-merge.
- **Deviation — data contract addition:** centre docs carry denormalized summary
  fields (`footfall_today`, `beds_total`, `beds_occupied`, `beds_available`)
  written by seed + recompute; beds/tests live at `centres/{id}/beds/current`
  and `centres/{id}/tests/current`.
- **Additions beyond plan (done):** dev preview harness (`VITE_PREVIEW=1`,
  `/?role=admin|operator`), PWA manifest + icon, Active Alerts panel with
  `POST /api/alerts/{id}/resolve`, recommendations acknowledge endpoint,
  language dropdown, responsive operator page, google-genai SDK migration.

---

## Phase 0 — Day 0: Setup & Foundations

### Task 0.1 (IN): Repo scaffold + backend skeleton

**Files:**
- Create: `smart-health/api/requirements.txt`, `smart-health/api/app/main.py`, `smart-health/api/app/config.py`, `smart-health/api/.env.example`, `smart-health/README.md`
- Test: `smart-health/api/tests/test_endpoints.py`

**Interfaces:**
- Produces: FastAPI `app` in `app.main`; `Settings` in `app.config` exposing `gemini_model: str`, `gemini_api_key: str`, `seed_enabled: bool`, `allowed_origin: str`.

- [x] **Step 1: Write requirements.txt**
```
fastapi==0.115.*
uvicorn[standard]==0.32.*
firebase-admin==6.5.*
google-generativeai==0.8.*
pydantic==2.9.*
pydantic-settings==2.5.*
slowapi==0.1.9
pytest==8.3.*
httpx==0.27.*
```

- [x] **Step 2: Write `app/config.py`**
```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    gemini_model: str = "gemini-2.5-flash"
    gemini_api_key: str = ""
    seed_enabled: bool = False
    allowed_origin: str = "http://localhost:5173"
    firebase_credentials_path: str = ""  # path to service-account JSON; empty = ADC

settings = Settings()
```

- [x] **Step 3: Write the failing test for the health endpoint**
```python
# tests/test_endpoints.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_ok():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
```

- [x] **Step 4: Run it, expect failure** — `cd smart-health/api && pytest tests/test_endpoints.py -v` → FAIL (no `app.main`).

- [x] **Step 5: Write `app/main.py`**
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.config import settings

limiter = Limiter(key_func=get_remote_address)

def create_app() -> FastAPI:
    app = FastAPI(title="Smart Health API")
    app.state.limiter = limiter
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.allowed_origin],
        allow_methods=["*"], allow_headers=["*"], allow_credentials=True,
    )

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app

app = create_app()
```

- [x] **Step 6: Run test, expect PASS.**

- [x] **Step 7: Write `.env.example`**
```
GEMINI_MODEL=gemini-2.5-flash
GEMINI_API_KEY=
SEED_ENABLED=false
ALLOWED_ORIGIN=http://localhost:5173
FIREBASE_CREDENTIALS_PATH=
```

- [x] **Step 8: Commit**
```bash
git add smart-health/api smart-health/README.md
git commit -m "feat: backend skeleton with health endpoint"
```

### Task 0.2 (AI): Verify Gemini model + spike

**Files:** Create: `smart-health/api/app/services/gemini.py` (initial), `smart-health/api/scripts/verify_gemini.py`

**Interfaces:**
- Produces: `gemini.generate(prompt: str, language: str = "mr") -> str` returning plain text.

- [x] **Step 1: Write `scripts/verify_gemini.py`** (run once, confirms the live model id)
```python
import google.generativeai as genai
from app.config import settings

genai.configure(api_key=settings.gemini_api_key)
print("Available flash models:")
for m in genai.list_models():
    if "generateContent" in m.supported_generation_methods and "flash" in m.name:
        print(" ", m.name)
```

- [x] **Step 2: Run it** — `python -m scripts.verify_gemini`. Expected: a list including `models/gemini-2.5-flash` (or a newer flash). **If `gemini-2.5-flash` is absent, update `GEMINI_MODEL` in `.env` to the newest listed flash id and note it in README.**

- [x] **Step 3: Write `app/services/gemini.py`**
```python
import google.generativeai as genai
from app.config import settings

genai.configure(api_key=settings.gemini_api_key)
_model = genai.GenerativeModel(settings.gemini_model)

_LANG = {"en": "English", "hi": "Hindi", "mr": "Marathi"}

def generate(prompt: str, language: str = "mr") -> str:
    full = f"{prompt}\n\nRespond in {_LANG.get(language, 'English')}. Be concise."
    try:
        return _model.generate_content(full).text.strip()
    except Exception as e:  # never let Gemini break a request
        return ""
```

- [x] **Step 4: Manual spike** — a throwaway call `generate("Summarise: PHC Mulshi paracetamol runs out in 3 days.", "en")` prints a real sentence. Confirm non-empty.

- [x] **Step 5: Commit**
```bash
git add smart-health/api/app/services/gemini.py smart-health/api/scripts
git commit -m "feat: gemini client + live model verification"
```

### Task 0.3 (IN): Firestore client + Firebase project

**Files:** Create: `smart-health/api/app/firestore_client.py`

**Interfaces:**
- Produces: `db` (Firestore client), `verify_id_token(token: str) -> dict` (wraps `firebase_admin.auth.verify_id_token`).

- [x] **Step 1: In the GCP console** enable Firestore (Native mode), Firebase Auth (Google provider), and generate a service-account key. Store its path in `.env` `FIREBASE_CREDENTIALS_PATH` (do NOT commit the JSON; add `*serviceaccount*.json` to `.gitignore`).

- [x] **Step 2: Write `app/firestore_client.py`**
```python
import firebase_admin
from firebase_admin import credentials, firestore, auth
from app.config import settings

if not firebase_admin._apps:
    cred = (credentials.Certificate(settings.firebase_credentials_path)
            if settings.firebase_credentials_path else credentials.ApplicationDefault())
    firebase_admin.initialize_app(cred)

db = firestore.client()

def verify_id_token(token: str) -> dict:
    return auth.verify_id_token(token)
```

- [x] **Step 3: Manual verify** — a throwaway script writes then reads a `/_ping` doc; confirm it round-trips in the Firestore console.

- [x] **Step 4: Commit**
```bash
git add smart-health/api/app/firestore_client.py smart-health/api/.gitignore
git commit -m "feat: firestore + firebase-admin client"
```

### Task 0.4 (FE): Frontend scaffold + Firebase Auth on localhost

**Files:** Create: `smart-health/web/` (Vite React), `web/src/firebase.js`, `web/.env.example`

**Interfaces:**
- Produces: `auth`, `db`, `googleProvider` from `firebase.js`; a working Google Sign-In button on `/` that logs the ID token to console.

- [x] **Step 1: Scaffold** — `npm create vite@latest web -- --template react`, then `npm i firebase axios recharts` and set up TailwindCSS (`npm i -D tailwindcss postcss autoprefixer && npx tailwindcss init -p`, configure `content` + `@tailwind` directives).

- [x] **Step 2: Write `web/.env.example`** (Vite needs `VITE_` prefix)
```
VITE_FIREBASE_API_KEY=
VITE_FIREBASE_AUTH_DOMAIN=
VITE_FIREBASE_PROJECT_ID=
VITE_API_BASE=http://localhost:8000
```

- [x] **Step 3: Write `web/src/firebase.js`**
```javascript
import { initializeApp } from "firebase/app";
import { getAuth, GoogleAuthProvider } from "firebase/auth";
import { initializeFirestore, persistentLocalCache } from "firebase/firestore";

const app = initializeApp({
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
});
export const auth = getAuth(app);
export const googleProvider = new GoogleAuthProvider();
// offline persistence for low-connectivity PHCs (Global Constraint)
export const db = initializeFirestore(app, { localCache: persistentLocalCache() });
```

- [x] **Step 4: Temporary sign-in button in `App.jsx`** calling `signInWithPopup(auth, googleProvider)` then `user.getIdToken().then(console.log)`.

- [ ] **Step 5: Verify** — `npm run dev`, click sign-in, confirm a Google account signs in and an ID token prints. (Add `localhost` is already an authorized domain by default.)

- [x] **Step 6: Commit**
```bash
git add smart-health/web
git commit -m "feat: web scaffold + firebase auth on localhost"
```

---

## Phase 1 — Day 1: Vertical Slice (login → stock → forecast, live)

### Task 1.1 (BE): Pydantic schemas + response envelope

**Files:** Create: `smart-health/api/app/models/schemas.py`

**Interfaces:**
- Produces: `ok(data) -> dict`, `Medicine`, `StockUpdate`, `BedsUpdate`, `FootfallLog`, `AttendanceLog`, `TestsUpdate` models used by routers.

- [x] **Step 1: Write `schemas.py`**
```python
from datetime import datetime, timezone
from pydantic import BaseModel, Field

def ok(data):
    return {"success": True, "data": data, "timestamp": datetime.now(timezone.utc).isoformat()}

def err(message: str, code: int):
    return {"success": False, "error": message, "code": code}

class StockUpdate(BaseModel):
    medicine_id: str
    current_stock: float = Field(ge=0)

class BedsUpdate(BaseModel):
    occupied: int = Field(ge=0)

class FootfallLog(BaseModel):
    count: int = Field(ge=0)
    opd: int = Field(ge=0, default=0)
    ipd: int = Field(ge=0, default=0)

class AttendanceLog(BaseModel):
    doctors_present: int = Field(ge=0)
    doctors_total: int = Field(gt=0)
    nurses_present: int = Field(ge=0, default=0)
    nurses_total: int = Field(ge=0, default=0)

class TestsUpdate(BaseModel):
    tests: dict[str, bool]
```

- [x] **Step 2: Commit** — `git add app/models/schemas.py && git commit -m "feat: pydantic schemas + response envelope"`

### Task 1.2 (BE): Auth dependency + role guards (TDD)

**Files:** Create: `app/deps.py`; Test: `tests/test_auth.py`

**Interfaces:**
- Consumes: `verify_id_token` (Task 0.3).
- Produces: `get_current_user() -> dict` with keys `uid, email, role, district_id, centre_id` (role/others `None` when claim absent); `require_role(role)` guard factory; `require_own_centre(centre_id, user)`.

- [x] **Step 1: Write failing tests**
```python
# tests/test_auth.py
import pytest
from fastapi import HTTPException
from app import deps

def test_unknown_user_has_null_role(monkeypatch):
    monkeypatch.setattr(deps, "verify_id_token", lambda t: {"uid": "u1", "email": "a@b.com"})
    user = deps._user_from_token("Bearer tok")
    assert user["role"] is None and user["uid"] == "u1"

def test_claims_are_read(monkeypatch):
    monkeypatch.setattr(deps, "verify_id_token",
        lambda t: {"uid": "u1", "email": "a@b.com", "role": "phc_operator",
                   "district_id": "pune_rural", "centre_id": "phc_mulshi"})
    user = deps._user_from_token("Bearer tok")
    assert user["role"] == "phc_operator" and user["centre_id"] == "phc_mulshi"

def test_missing_token_401():
    with pytest.raises(HTTPException) as e:
        deps._user_from_token(None)
    assert e.value.status_code == 401

def test_require_role_rejects_wrong_role():
    guard = deps.require_role("district_admin")
    with pytest.raises(HTTPException) as e:
        guard({"role": "phc_operator"})
    assert e.value.status_code == 403
```

- [x] **Step 2: Run, expect FAIL.**

- [x] **Step 3: Write `app/deps.py`**
```python
from fastapi import Header, HTTPException, Depends
from app.firestore_client import verify_id_token

def _user_from_token(authorization: str | None) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1]
    try:
        claims = verify_id_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {
        "uid": claims.get("uid") or claims.get("user_id"),
        "email": claims.get("email"),
        "role": claims.get("role"),
        "district_id": claims.get("district_id"),
        "centre_id": claims.get("centre_id"),
    }

def get_current_user(authorization: str | None = Header(default=None)) -> dict:
    return _user_from_token(authorization)

def require_role(role: str):
    def guard(user: dict = Depends(get_current_user)) -> dict:
        if user.get("role") != role:
            raise HTTPException(status_code=403, detail="Forbidden")
        return user
    return guard

def require_own_centre(centre_id: str, user: dict):
    if user.get("role") != "phc_operator" or user.get("centre_id") != centre_id:
        raise HTTPException(status_code=403, detail="Not your centre")
```

- [x] **Step 4: Run, expect PASS.**

- [x] **Step 5: Commit** — `git commit -am "feat: auth dependency + role guards"`

### Task 1.3 (AI): EWMA forecasting (TDD)

**Files:** Create: `app/services/forecasting.py`; Test: `tests/test_forecasting.py`

**Interfaces:**
- Produces: `ewma(series: list[float], alpha=0.3) -> float`; `forecast_stockout(history: list[float], current_stock: float) -> dict` with keys `days_remaining, daily_consumption_forecast, predicted_stockout_date, severity, trend`; `forecast_footfall(history: list[int]) -> dict` with keys `projection, trend`.

- [x] **Step 1: Write failing tests**
```python
# tests/test_forecasting.py
from app.services import forecasting as f

def test_ewma_weights_recent_higher():
    assert f.ewma([10, 10, 10]) == 10
    assert f.ewma([0, 0, 20]) > f.ewma([20, 0, 0])

def test_stockout_severity_critical_at_three_days():
    r = f.forecast_stockout([10, 10, 10], current_stock=25)  # ~2.5 days
    assert r["severity"] == "critical"
    assert r["days_remaining"] <= 3

def test_stockout_low_when_ample():
    r = f.forecast_stockout([10, 10, 10], current_stock=1000)
    assert r["severity"] == "low"

def test_footfall_trend_falling():
    r = f.forecast_footfall([80, 70, 60, 50, 40])
    assert r["trend"] == "falling"
```

- [x] **Step 2: Run, expect FAIL.**

- [x] **Step 3: Write `app/services/forecasting.py`**
```python
from datetime import datetime, timedelta, timezone

def ewma(series: list[float], alpha: float = 0.3) -> float:
    # Normalized recency-weighted average: newest gets weight 1, older decay by (1-alpha).
    # NOTE: the naive seeded recursion (acc=series[0]; acc=alpha*x+(1-alpha)*acc) over-weights
    # the OLDEST value on short series with alpha<0.5, contradicting "recent weighted higher".
    if not series:
        return 0.0
    n = len(series)
    num = den = 0.0
    for i, x in enumerate(series):
        w = (1 - alpha) ** (n - 1 - i)  # newest (i=n-1) -> weight 1.0
        num += w * x
        den += w
    return num / den

def forecast_stockout(history: list[float], current_stock: float) -> dict:
    rate = ewma(history)
    days = current_stock / rate if rate > 0 else 999.0
    if days <= 3:    sev = "critical"
    elif days <= 7:  sev = "high"
    elif days <= 14: sev = "medium"
    else:            sev = "low"
    return {
        "days_remaining": round(days, 1),
        "daily_consumption_forecast": round(rate, 2),
        "predicted_stockout_date": (datetime.now(timezone.utc) + timedelta(days=days)).isoformat(),
        "severity": sev,
        "trend": "increasing" if history and history[-1] > rate else "stable",
    }

def forecast_footfall(history: list[int]) -> dict:
    rate = ewma([float(x) for x in history])
    trend = "stable"
    if len(history) >= 2:
        if history[-1] < rate * 0.9:   trend = "falling"
        elif history[-1] > rate * 1.1: trend = "rising"
    return {"projection": round(rate), "trend": trend}
```

- [x] **Step 4: Run, expect PASS.**
- [x] **Step 5: Commit** — `git commit -am "feat: EWMA stock-out + footfall forecasting"`

### Task 1.4 (BE): Minimal seed — provision accounts + one centre's stock

**Files:** Create: `app/seed/demo_data.py`, `app/routers/seed.py`; Modify: `app/main.py` (mount router)

**Interfaces:**
- Consumes: `db` (0.3), `settings.seed_enabled`, `require_role` (1.2), `forecast_stockout` (1.3).
- Produces: `POST /api/seed/district` and `POST /api/seed/reset`; `seed/demo_data.py::seed_district()` and `provision_accounts()`.

- [x] **Step 1: Write `app/seed/demo_data.py`** (minimal now; expanded in Task 2.1)
```python
from firebase_admin import auth
from app.firestore_client import db

DISTRICT = {"id": "pune_rural", "name": "Pune Rural District", "state": "Maharashtra"}

# email -> (role, centre_id). Create these Google accounts OR use your own emails for the demo.
DEMO_ACCOUNTS = {
    "admin@pune.gov.in":    ("district_admin", None),
    "mulshi@pune.gov.in":   ("phc_operator", "phc_mulshi"),
    "haveli@pune.gov.in":   ("phc_operator", "phc_haveli"),
}

def provision_accounts():
    """Set custom claims on existing Firebase users; skip if the user hasn't signed in yet."""
    for email, (role, centre_id) in DEMO_ACCOUNTS.items():
        try:
            u = auth.get_user_by_email(email)
            auth.set_custom_user_claims(u.uid, {
                "role": role, "district_id": DISTRICT["id"], "centre_id": centre_id})
        except auth.UserNotFoundError:
            pass  # they claim their role after first sign-in; re-run seed then

def seed_district():
    db.collection("districts").document(DISTRICT["id"]).set(
        {"name": DISTRICT["name"], "state": DISTRICT["state"], "total_centres": 6})
    db.collection("centres").document("phc_mulshi").set(
        {"name": "PHC Mulshi", "type": "PHC", "district_id": DISTRICT["id"], "status": "operational"})
    # one medicine to prove the slice
    db.collection("centres").document("phc_mulshi").collection("stock").document("paracetamol").set(
        {"medicine_name": "Paracetamol 500mg", "unit": "tablets", "current_stock": 120,
         "reorder_level": 200, "min_threshold": 100, "daily_consumption_avg": 40,
         "consumption_history": [38, 41, 40, 42, 39]})
    provision_accounts()
```

- [x] **Step 2: Write `app/routers/seed.py`**
```python
from fastapi import APIRouter, Depends, HTTPException
from app.config import settings
from app.deps import require_role
from app.models.schemas import ok
from app.seed import demo_data

router = APIRouter(prefix="/api/seed", tags=["seed"])

def _guard():
    if not settings.seed_enabled:
        raise HTTPException(status_code=403, detail="Seeding disabled")

@router.post("/district")
def seed(_=Depends(_guard), user=Depends(require_role("district_admin"))):
    demo_data.seed_district()
    return ok({"seeded": True})
```

- [x] **Step 3: Mount in `main.py`** — `from app.routers import seed` then `app.include_router(seed.router)` inside `create_app`.

- [x] **Step 4: Verify** — set `SEED_ENABLED=true`, sign in as the admin account (claim it first — see Task 1.5 Step 4), `curl -X POST localhost:8000/api/seed/district -H "Authorization: Bearer <admin_token>"` → `{"success": true, ...}`; confirm the docs in Firestore console.

- [x] **Step 5: Commit** — `git commit -am "feat: minimal seed + gated seed router"`

### Task 1.5 (BE): Read endpoints — centre stock (TDD via TestClient)

**Files:** Create: `app/routers/centres.py`; Modify: `main.py`; Test: extend `tests/test_endpoints.py`

**Interfaces:**
- Consumes: `db`, `get_current_user`, `ok`.
- Produces: `GET /api/centres/{centre_id}/stock` → `ok({medicines: [...]})`; each medicine includes forecast fields merged from `forecast_stockout`.

- [x] **Step 1: Write failing test** (mock `db` via a fake to avoid live Firestore in unit tests)
```python
# tests/test_endpoints.py (add)
def test_stock_requires_auth():
    r = client.get("/api/centres/phc_mulshi/stock")
    assert r.status_code == 401
```

- [x] **Step 2: Run, expect FAIL** (route missing → 404, so first mount an empty router; the auth-first ordering makes it 401 once implemented).

- [x] **Step 3: Write `app/routers/centres.py`**
```python
from fastapi import APIRouter, Depends
from app.deps import get_current_user
from app.firestore_client import db
from app.models.schemas import ok
from app.services.forecasting import forecast_stockout

router = APIRouter(prefix="/api/centres", tags=["centres"])

@router.get("/{centre_id}/stock")
def get_stock(centre_id: str, user=Depends(get_current_user)):
    out = []
    for doc in db.collection("centres").document(centre_id).collection("stock").stream():
        m = doc.to_dict() | {"id": doc.id}
        fc = forecast_stockout(m.get("consumption_history", []), m.get("current_stock", 0))
        out.append(m | fc)
    return ok({"medicines": out})
```

- [x] **Step 4: Mount router; run test, expect PASS (401 without token).**

- [ ] **Step 5: Manual claim + verify** — first-time role assignment: after the admin signs in once, run `provision_accounts()` (or re-run seed) so claims attach; then `curl .../stock -H "Authorization: Bearer <token>"` returns the medicine with `days_remaining` and `severity: "critical"`.

- [x] **Step 6: Commit** — `git commit -am "feat: centre stock read endpoint with forecast"`

### Task 1.6 (AI): Forecast endpoint + Gemini narrative

**Files:** Create: `app/routers/ai.py`; Modify: `main.py`

**Interfaces:**
- Consumes: `forecast_stockout`, `gemini.generate`, `db`.
- Produces: `GET /api/ai/forecast/{centre_id}` → `ok({medicines:[...], narrative: "<gemini text>"})`.

- [x] **Step 1: Write `app/routers/ai.py`**
```python
from fastapi import APIRouter, Depends, Query
from app.deps import get_current_user
from app.firestore_client import db
from app.models.schemas import ok
from app.services.forecasting import forecast_stockout
from app.services import gemini

router = APIRouter(prefix="/api/ai", tags=["ai"])

@router.get("/forecast/{centre_id}")
def forecast(centre_id: str, lang: str = Query("mr"), user=Depends(get_current_user)):
    meds = []
    for doc in db.collection("centres").document(centre_id).collection("stock").stream():
        m = doc.to_dict()
        fc = forecast_stockout(m.get("consumption_history", []), m.get("current_stock", 0))
        meds.append({"name": m.get("medicine_name"), **fc})
    at_risk = [m for m in meds if m["severity"] in ("critical", "high")]
    narrative = gemini.generate(
        "You are a district health supply officer. Medicines at risk: "
        + "; ".join(f'{m["name"]} ({m["days_remaining"]}d)' for m in at_risk)
        + ". Write a 2-sentence alert.", lang) if at_risk else ""
    return ok({"medicines": meds, "narrative": narrative})
```

- [x] **Step 2: Mount router. Manual verify** — `curl .../api/ai/forecast/phc_mulshi?lang=en` returns medicines + a non-empty narrative sentence.

- [x] **Step 3: Commit** — `git commit -am "feat: AI forecast endpoint with gemini narrative"`

### Task 1.7 (FE): Login, role routing, not-provisioned, useAuth

**Files:** Create: `web/src/hooks/useAuth.js`, `web/src/api.js`, `web/src/pages/{Login,NotProvisioned}.jsx`; Modify: `App.jsx`

**Interfaces:**
- Consumes: `auth`, `googleProvider`, ID-token custom claims.
- Produces: `useAuth() -> {user, role, loading, signIn, signOut}` where `role` comes from `getIdTokenResult().claims.role`; axios `api` instance that injects the token and unwraps the envelope.

- [x] **Step 1: Write `web/src/api.js`**
```javascript
import axios from "axios";
import { auth } from "./firebase";

export const api = axios.create({ baseURL: import.meta.env.VITE_API_BASE });
api.interceptors.request.use(async (cfg) => {
  const u = auth.currentUser;
  if (u) cfg.headers.Authorization = `Bearer ${await u.getIdToken()}`;
  return cfg;
});
api.interceptors.response.use(
  (r) => (r.data?.success ? r.data.data : Promise.reject(r.data)),
  (e) => Promise.reject(e.response?.data || e)
);
```

- [x] **Step 2: Write `web/src/hooks/useAuth.js`**
```javascript
import { useEffect, useState } from "react";
import { onAuthStateChanged, signInWithPopup, signOut as fbSignOut } from "firebase/auth";
import { auth, googleProvider } from "../firebase";

export function useAuth() {
  const [user, setUser] = useState(null);
  const [role, setRole] = useState(undefined); // undefined=loading, null=unprovisioned
  const [loading, setLoading] = useState(true);
  useEffect(() => onAuthStateChanged(auth, async (u) => {
    setUser(u);
    if (u) {
      const res = await u.getIdTokenResult(true);
      setRole(res.claims.role ?? null);
    } else setRole(undefined);
    setLoading(false);
  }), []);
  return {
    user, role, loading,
    signIn: () => signInWithPopup(auth, googleProvider),
    signOut: () => fbSignOut(auth),
  };
}
```

- [x] **Step 3: Write `App.jsx` routing**
```javascript
import { useAuth } from "./hooks/useAuth";
import Login from "./pages/Login";
import NotProvisioned from "./pages/NotProvisioned";
// import Dashboard, MyCentre (added in later tasks — stub with <div/> for now)

export default function App() {
  const { user, role, loading, signIn, signOut } = useAuth();
  if (loading) return <div className="p-8">Loading…</div>;
  if (!user) return <Login onSignIn={signIn} />;
  if (role === null) return <NotProvisioned email={user.email} onSignOut={signOut} />;
  if (role === "district_admin") return <div>Dashboard (Task 2.10)</div>;
  if (role === "phc_operator") return <div>My Centre (Task 3.3)</div>;
  return <NotProvisioned email={user.email} onSignOut={signOut} />;
}
```

- [x] **Step 4: Write `Login.jsx` and `NotProvisioned.jsx`** — Login: product title + "Sign in with Google" button calling `onSignIn`. NotProvisioned: "Account not yet provisioned — contact your district admin" + email + sign-out. (Visual polish via Claude Design later; functional now.)

- [ ] **Step 5: Verify** — sign in with an account that has NO claim → NotProvisioned screen. Provision it (seed), refresh → routes to the correct role stub.

- [x] **Step 6: Commit** — `git commit -am "feat: login, role routing, not-provisioned, useAuth + api client"`

### Task 1.8 (FE): useFirestore onSnapshot — one live card

**Files:** Create: `web/src/hooks/useFirestore.js`

**Interfaces:**
- Produces: `useCollection(path, constraints?) -> array` re-rendering on `onSnapshot`; `useDoc(path) -> object|null`.

- [x] **Step 1: Write `web/src/hooks/useFirestore.js`**
```javascript
import { useEffect, useState } from "react";
import { collection, doc, onSnapshot, query } from "firebase/firestore";
import { db } from "../firebase";

export function useCollection(path, constraints = []) {
  const [rows, setRows] = useState([]);
  useEffect(() => {
    const q = query(collection(db, path), ...constraints);
    return onSnapshot(q, (snap) => setRows(snap.docs.map((d) => ({ id: d.id, ...d.data() }))));
  }, [path, JSON.stringify(constraints.map(String))]);
  return rows;
}

export function useDoc(path) {
  const [data, setData] = useState(null);
  useEffect(() => onSnapshot(doc(db, path), (d) => setData(d.exists() ? { id: d.id, ...d.data() } : null)), [path]);
  return data;
}
```

- [ ] **Step 2: Verify live update** — a temporary component renders `useDoc("centres/phc_mulshi").status`; change the field in Firestore console; the screen updates within ~1–2s without refresh. **This proves the real-time backbone.**

- [x] **Step 3: Commit** — `git commit -am "feat: firestore onSnapshot hooks + live update proof"`

**Day 1 gate:** Log in as admin → see PHC Mulshi's stock (paracetamol, 3 days, critical) → hit `/api/ai/forecast` → get a Gemini narrative. A Firestore console edit updates the UI live.

---

## Phase 2 — Day 2: Core Features (all centres, alerts, redistribution, AI)

### Task 2.1 (BE): Full demo seed — 6 centres + 30-day history

**Files:** Modify: `app/seed/demo_data.py`

**Interfaces:**
- Produces: `seed_district()` writing all 6 centres per the spec scenario, each with stock (with `consumption_history`), beds, `/attendance/{YYYYMMDD}` and `/footfall/{YYYYMMDD}` for the last 30 days, and `/tests` (+`essential`).

- [x] **Step 1: Replace `seed_district()`** with the full generator. Encode the spec scenario exactly:
  - PHC Mulshi: Paracetamol 120 stock / avg ~40 → ~3 days (critical); attendance ~60%.
  - PHC Haveli: ORS Sachets 90 / avg ~45 → ~2 days (critical).
  - PHC Ambegaon: Iron+Folic 450 / avg ~90 → ~5 days (warning).
  - Pune Rural CHC: Paracetamol surplus (e.g. 900, reorder 200) → donor.
  - PHC Velhe: low footfall (~40 vs district ~78), attendance ~52%, 1 essential test off → underperformer.
  - PHC Bhor: all healthy.
  Generate 30 days of footfall/attendance with `for i in range(30): date=(today-timedelta(days=i))`. Use fixed values (no randomness) so the demo is reproducible.
```python
from datetime import datetime, timedelta, timezone
def _days(n):
    base = datetime.now(timezone.utc).date()
    return [(base - timedelta(days=i)).strftime("%Y%m%d") for i in range(n)]
# for each centre: write stock/*, beds, attendance/*, footfall/*, tests
# (write consumption_history as the last ~7 daily consumption values per medicine)
```

- [x] **Step 2: Verify** — reseed; Firestore console shows 6 centres each with populated subcollections; footfall/attendance have 30 docs.

- [x] **Step 3: Commit** — `git commit -am "feat: full Pune Rural District demo seed"`

### Task 2.2 (AI): Underperformance scoring (TDD)

**Files:** Create: `app/services/scoring.py`; Test: `tests/test_scoring.py`

**Interfaces:**
- Produces: `compute_performance_score(centre: dict) -> {score:int, flags:list[str], status:str}`. Input keys: `avg_attendance_rate`, `avg_footfall`, `district_avg_footfall`, `critical_stockouts:int`, `bed_occupancy_rate`, `essential_tests_unavailable:int`.

- [x] **Step 1: Write failing tests**
```python
from app.services.scoring import compute_performance_score

def test_healthy_centre_scores_high():
    r = compute_performance_score({"avg_attendance_rate":0.9,"avg_footfall":80,
        "district_avg_footfall":78,"critical_stockouts":0,"bed_occupancy_rate":0.6,
        "essential_tests_unavailable":0})
    assert r["score"] >= 90 and r["status"] == "operational"

def test_velhe_flagged_underperforming():
    r = compute_performance_score({"avg_attendance_rate":0.52,"avg_footfall":40,
        "district_avg_footfall":78,"critical_stockouts":1,"bed_occupancy_rate":0.2,
        "essential_tests_unavailable":1})
    assert r["status"] in ("critical","under_resourced")
    assert any("attendance" in f.lower() for f in r["flags"])
```

- [x] **Step 2: Run, expect FAIL.**

- [x] **Step 3: Write `app/services/scoring.py`** (weights per spec §6.3: attendance 25, footfall 20, stockouts 20, beds 15, tests 20)
```python
def compute_performance_score(c: dict) -> dict:
    score, flags = 100, []
    if c["avg_attendance_rate"] < 0.6:
        score -= min((0.6 - c["avg_attendance_rate"]) * 100, 25)
        flags.append(f"Doctor attendance {c['avg_attendance_rate']*100:.0f}% (target 80%)")
    if c["district_avg_footfall"] and c["avg_footfall"] / c["district_avg_footfall"] < 0.6:
        score -= 20
        flags.append(f"Footfall {c['avg_footfall']/c['district_avg_footfall']*100:.0f}% of district average")
    if c["critical_stockouts"]:
        score -= min(c["critical_stockouts"] * 8, 20)
        flags.append(f"{c['critical_stockouts']} medicine(s) in critical stock-out")
    if c["bed_occupancy_rate"] < 0.3:
        score -= 15
        flags.append(f"Bed occupancy {c['bed_occupancy_rate']*100:.0f}% — underutilised")
    if c["essential_tests_unavailable"]:
        score -= min(c["essential_tests_unavailable"] * 10, 20)
        flags.append(f"{c['essential_tests_unavailable']} essential test(s) unavailable")
    score = max(0, round(score))
    status = "critical" if score < 40 else "under_resourced" if score < 65 else "operational"
    return {"score": score, "flags": flags, "status": status}
```

- [x] **Step 4: Run, expect PASS. Commit** — `git commit -am "feat: underperformance scoring"`

### Task 2.3 (AI): Redistribution engine (TDD)

**Files:** Create: `app/services/redistribution.py`; Test: `tests/test_redistribution.py`

**Interfaces:**
- Produces: `compute_redistribution(centres: list[dict]) -> list[dict]`. Each centre: `{id, name, stock: {med: {current_stock, reorder_level, daily_avg, days_remaining}}}`. Output items: `{from_centre, to_centre, medicine, quantity, urgency}`.

- [x] **Step 1: Write failing test**
```python
from app.services.redistribution import compute_redistribution

def test_surplus_flows_to_deficit():
    centres = [
      {"id":"chc","name":"CHC","stock":{"para":{"current_stock":900,"reorder_level":200,"daily_avg":30,"days_remaining":30}}},
      {"id":"mulshi","name":"Mulshi","stock":{"para":{"current_stock":120,"reorder_level":200,"daily_avg":40,"days_remaining":3}}},
    ]
    recs = compute_redistribution(centres)
    assert len(recs) == 1
    assert recs[0]["from_centre"] == "CHC" and recs[0]["to_centre"] == "Mulshi"
    assert recs[0]["quantity"] > 0
```

- [x] **Step 2: Run, expect FAIL.**

- [x] **Step 3: Write `app/services/redistribution.py`**
```python
def compute_redistribution(centres: list[dict]) -> list[dict]:
    recs = []
    meds = {m for c in centres for m in c["stock"]}
    for med in meds:
        surplus = sorted(
            [c for c in centres if c["stock"].get(med, {}).get("current_stock", 0)
             > c["stock"].get(med, {}).get("reorder_level", 0) * 1.5],
            key=lambda c: -c["stock"][med]["current_stock"])
        deficit = sorted(
            [c for c in centres if c["stock"].get(med, {}).get("days_remaining", 999) <= 7],
            key=lambda c: c["stock"][med]["days_remaining"])
        for needy in deficit:
            if not surplus: break
            donor = surplus[0]
            need = (14 - needy["stock"][med]["days_remaining"]) * needy["stock"][med]["daily_avg"]
            avail = donor["stock"][med]["current_stock"] - donor["stock"][med]["reorder_level"]
            qty = round(min(need, avail))
            if qty <= 0: continue
            recs.append({"from_centre": donor["name"], "to_centre": needy["name"],
                         "medicine": med, "quantity": qty,
                         "urgency": "critical" if needy["stock"][med]["days_remaining"] <= 3 else "high"})
            donor["stock"][med]["current_stock"] -= qty
            if donor["stock"][med]["current_stock"] <= donor["stock"][med]["reorder_level"] * 1.5:
                surplus.pop(0)
    return recs
```

- [x] **Step 4: Run, expect PASS. Commit** — `git commit -am "feat: greedy redistribution engine"`

### Task 2.4 (BE): Alert generation — templates, Gemini-free (TDD)

**Files:** Create: `app/services/alerting.py`; Test: `tests/test_alerting.py`

**Interfaces:**
- Produces: `build_alerts(centre_id, centre_name, district_id, stock_forecasts, beds, attendance_rate, tests) -> list[dict]` returning alert docs with `type, severity, message, medicine_name, days_remaining, resolved=False`. No Gemini.

- [x] **Step 1: Write failing tests**
```python
from app.services.alerting import build_alerts

def test_critical_stockout_alert():
    alerts = build_alerts("phc_mulshi","PHC Mulshi","pune_rural",
        [{"medicine_name":"Paracetamol 500mg","days_remaining":3,"severity":"critical"}],
        beds={"available":5}, attendance_rate=0.8, tests={"malaria":True,"tb":True,"pregnancy":True})
    a = [x for x in alerts if x["type"]=="STOCKOUT_CRITICAL"]
    assert a and "Paracetamol" in a[0]["message"] and a[0]["resolved"] is False

def test_bed_crisis_and_test_unavailable():
    alerts = build_alerts("c","C","d", [], beds={"available":0}, attendance_rate=0.9,
        tests={"malaria":False,"tb":True,"pregnancy":True})
    types = {x["type"] for x in alerts}
    assert "BED_CRISIS" in types and "TEST_UNAVAILABLE" in types
```

- [x] **Step 2: Run, expect FAIL.**

- [x] **Step 3: Write `app/services/alerting.py`**
```python
ESSENTIAL = ("malaria", "tb", "pregnancy")

def build_alerts(centre_id, centre_name, district_id, stock_forecasts, beds, attendance_rate, tests):
    alerts, base = [], {"centre_id": centre_id, "centre_name": centre_name,
                        "district_id": district_id, "resolved": False}
    for m in stock_forecasts:
        if m["severity"] == "critical":
            alerts.append(base | {"type": "STOCKOUT_CRITICAL", "severity": "critical",
                "medicine_name": m["medicine_name"], "days_remaining": m["days_remaining"],
                "message": f'{m["medicine_name"]} will stock out in {m["days_remaining"]} days — reorder now'})
        elif m["severity"] == "high":
            alerts.append(base | {"type": "STOCKOUT_WARNING", "severity": "high",
                "medicine_name": m["medicine_name"], "days_remaining": m["days_remaining"],
                "message": f'{m["medicine_name"]} low: {m["days_remaining"]} days remaining'})
    if beds and beds.get("available", 1) == 0:
        alerts.append(base | {"type": "BED_CRISIS", "severity": "high", "message": "No beds available"})
    if attendance_rate is not None and attendance_rate < 0.6:
        alerts.append(base | {"type": "ATTENDANCE_LOW", "severity": "medium",
            "message": f"Doctor attendance {attendance_rate*100:.0f}% — below 60%"})
    for t in ESSENTIAL:
        if tests and tests.get(t) is False:
            alerts.append(base | {"type": "TEST_UNAVAILABLE", "severity": "medium",
                "message": f"Essential test unavailable: {t}"})
    return alerts
```

- [x] **Step 4: Run, expect PASS. Commit** — `git commit -am "feat: template-based alert generation"`

### Task 2.5 (BE): Recompute-on-write + operator write endpoints

**Files:** Create: `app/services/recompute.py`, `app/routers/operator.py`; Modify: `main.py`

**Interfaces:**
- Consumes: `forecast_stockout`, `compute_performance_score`, `build_alerts`, `db`, `require_own_centre`.
- Produces: `recompute_centre(centre_id)` (writes back `days_remaining`/`predicted_stockout_date` per medicine, `performance_score`, `status`, replaces that centre's active alerts). Endpoints: `PATCH /api/centres/{id}/stock`, `/beds`, `POST /api/centres/{id}/footfall`, `/attendance`, `PATCH /api/centres/{id}/tests`.

- [x] **Step 1: Write `app/services/recompute.py`**
```python
from firebase_admin import firestore
from app.firestore_client import db
from app.services.forecasting import forecast_stockout
from app.services.scoring import compute_performance_score
from app.services import alerting

def recompute_centre(centre_id: str):
    cref = db.collection("centres").document(centre_id)
    centre = cref.get().to_dict() or {}
    # stock forecasts
    forecasts = []
    for doc in cref.collection("stock").stream():
        m = doc.to_dict()
        fc = forecast_stockout(m.get("consumption_history", []), m.get("current_stock", 0))
        doc.reference.update({"days_remaining": fc["days_remaining"],
                              "predicted_stockout_date": fc["predicted_stockout_date"]})
        forecasts.append({"medicine_name": m.get("medicine_name"), **fc})
    beds = (cref.collection("beds").document("current").get().to_dict()) or {}
    tests = (cref.collection("tests").document("current").get().to_dict()) or {}
    # attendance rate = latest attendance doc
    att_docs = list(cref.collection("attendance").order_by("date", direction="DESCENDING").limit(1).stream())
    att_rate = (att_docs[0].to_dict().get("attendance_rate") if att_docs else None)
    # score (district avg passed in via centre doc or recomputed elsewhere; use stored value)
    score = compute_performance_score({
        "avg_attendance_rate": att_rate or 1.0,
        "avg_footfall": centre.get("avg_footfall", 0),
        "district_avg_footfall": centre.get("district_avg_footfall", 1),
        "critical_stockouts": sum(1 for f in forecasts if f["severity"] == "critical"),
        "bed_occupancy_rate": (beds.get("occupied",0)/beds["total"]) if beds.get("total") else 0.5,
        "essential_tests_unavailable": sum(1 for t in alerting.ESSENTIAL if tests.get(t) is False),
    })
    cref.update({"performance_score": score["score"], "status": score["status"]})
    # replace active alerts for this centre
    for a in db.collection("alerts").where("centre_id","==",centre_id).where("resolved","==",False).stream():
        a.reference.delete()
    for a in alerting.build_alerts(centre_id, centre.get("name"), centre.get("district_id"),
                                   forecasts, beds, att_rate, tests):
        db.collection("alerts").add({**a, "created_at": firestore.SERVER_TIMESTAMP})
    return score
```

- [x] **Step 2: Write `app/routers/operator.py`**
```python
from fastapi import APIRouter, Depends
from app.deps import get_current_user, require_own_centre
from app.firestore_client import db
from app.models.schemas import ok, StockUpdate, BedsUpdate, FootfallLog, AttendanceLog, TestsUpdate
from app.services.recompute import recompute_centre
from datetime import datetime, timezone

router = APIRouter(prefix="/api/centres", tags=["operator"])

@router.patch("/{centre_id}/stock")
def update_stock(centre_id: str, body: StockUpdate, user=Depends(get_current_user)):
    require_own_centre(centre_id, user)
    db.collection("centres").document(centre_id).collection("stock").document(body.medicine_id)\
      .update({"current_stock": body.current_stock})
    score = recompute_centre(centre_id)
    return ok({"recomputed": score})

@router.patch("/{centre_id}/beds")
def update_beds(centre_id: str, body: BedsUpdate, user=Depends(get_current_user)):
    require_own_centre(centre_id, user)
    ref = db.collection("centres").document(centre_id).collection("beds").document("current")
    total = (ref.get().to_dict() or {}).get("total", 0)
    ref.update({"occupied": body.occupied, "available": max(0, total - body.occupied)})
    return ok({"recomputed": recompute_centre(centre_id)})

@router.post("/{centre_id}/footfall")
def log_footfall(centre_id: str, body: FootfallLog, user=Depends(get_current_user)):
    require_own_centre(centre_id, user)
    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    db.collection("centres").document(centre_id).collection("footfall").document(day)\
      .set({"date": day, **body.model_dump()})
    return ok({"recomputed": recompute_centre(centre_id)})

@router.post("/{centre_id}/attendance")
def log_attendance(centre_id: str, body: AttendanceLog, user=Depends(get_current_user)):
    require_own_centre(centre_id, user)
    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    rate = body.doctors_present / body.doctors_total
    db.collection("centres").document(centre_id).collection("attendance").document(day)\
      .set({"date": day, **body.model_dump(), "attendance_rate": rate})
    return ok({"recomputed": recompute_centre(centre_id)})

@router.patch("/{centre_id}/tests")
def update_tests(centre_id: str, body: TestsUpdate, user=Depends(get_current_user)):
    require_own_centre(centre_id, user)
    db.collection("centres").document(centre_id).collection("tests").document("current").set(body.tests, merge=True)
    return ok({"recomputed": recompute_centre(centre_id)})
```
  *(Adjust beds/tests to live under a `current` doc; update seed in Task 2.1 to write `beds/current` and `tests/current` accordingly.)*

- [x] **Step 3: Mount router. Manual verify** — as a `phc_operator` for Mulshi, `PATCH .../phc_mulshi/stock {"medicine_id":"paracetamol","current_stock":80}` → recompute returns a score; a new `STOCKOUT_CRITICAL` alert appears in `/alerts`; a cross-centre write (different centre_id) returns 403.

- [x] **Step 4: Commit** — `git commit -am "feat: operator write endpoints + recompute-on-write"`

### Task 2.6 (BE): District overview + alerts endpoints

**Files:** Modify: `app/routers/dashboard.py` (create), `main.py`

**Interfaces:**
- Produces: `GET /api/district/{id}/overview` → `ok({centres:[...], counts:{critical,total}, beds:{total,available}})`; `GET /api/district/{id}/alerts?resolved=false` → `ok({alerts:[...]})`.

- [x] **Step 1: Write `app/routers/dashboard.py`**
```python
from fastapi import APIRouter, Depends, Query
from app.deps import get_current_user
from app.firestore_client import db
from app.models.schemas import ok

router = APIRouter(prefix="/api/district", tags=["dashboard"])

@router.get("/{district_id}/overview")
def overview(district_id: str, user=Depends(get_current_user)):
    centres = [{"id": d.id, **d.to_dict()} for d in
               db.collection("centres").where("district_id","==",district_id).stream()]
    alerts = list(db.collection("alerts").where("district_id","==",district_id)
                  .where("resolved","==",False).stream())
    critical = sum(1 for a in alerts if a.to_dict().get("severity") == "critical")
    return ok({"centres": centres, "counts": {"critical": critical, "total_alerts": len(alerts),
               "total_centres": len(centres)}})

@router.get("/{district_id}/alerts")
def alerts(district_id: str, resolved: bool = Query(False), user=Depends(get_current_user)):
    q = (db.collection("alerts").where("district_id","==",district_id)
         .where("resolved","==",resolved))
    return ok({"alerts": [{"id": d.id, **d.to_dict()} for d in q.stream()]})
```

- [ ] **Step 2: Mount. Verify** — `curl .../api/district/pune_rural/overview` returns 6 centres; `/alerts` returns the active alerts. *(If Firestore errors asking for an index, create it — Task 4.2 formalises this.)*

- [x] **Step 3: Commit** — `git commit -am "feat: district overview + alerts endpoints"`

### Task 2.7 (AI): Remaining AI endpoints — briefing, redistribution, explain

**Files:** Modify: `app/routers/ai.py`; Create: cache util inline.

**Interfaces:**
- Produces: `GET /api/ai/district-briefing/{district_id}` (cached 15 min, invalidated on new critical alert); `POST /api/ai/redistribution/{district_id}` (writes `/recommendations`); `POST /api/ai/explain-underperformance/{centre_id}`.

- [x] **Step 1: Add briefing with in-memory cache**
```python
import time
_cache = {}  # district_id -> (text, expires_at, critical_count)

@router.get("/district-briefing/{district_id}")
def briefing(district_id: str, lang: str = "mr", user=Depends(get_current_user)):
    alerts = [a.to_dict() for a in db.collection("alerts")
              .where("district_id","==",district_id).where("resolved","==",False).stream()]
    crit = sum(1 for a in alerts if a.get("severity") == "critical")
    hit = _cache.get(district_id)
    if hit and hit[1] > time.time() and hit[2] == crit:
        return ok({"briefing": hit[0], "cached": True})
    text = gemini.generate(
        f"District has {len(alerts)} active alerts, {crit} critical: "
        + "; ".join(a.get("message","") for a in alerts[:6])
        + ". Write a 3-sentence executive briefing for the District Health Officer, most urgent first.",
        lang)
    _cache[district_id] = (text, time.time() + 900, crit)
    return ok({"briefing": text, "cached": False})
```

- [x] **Step 2: Add redistribution** — read all centres' stock, shape into the `compute_redistribution` input, call it, Gemini-phrase each, write to `/recommendations`, return them.
```python
@router.post("/redistribution/{district_id}")
def redistribution(district_id: str, lang: str = "mr", user=Depends(get_current_user)):
    from app.services.redistribution import compute_redistribution
    from app.services.forecasting import forecast_stockout
    centres = []
    for c in db.collection("centres").where("district_id","==",district_id).stream():
        stock = {}
        for s in c.reference.collection("stock").stream():
            m = s.to_dict()
            fc = forecast_stockout(m.get("consumption_history", []), m.get("current_stock", 0))
            stock[s.id] = {"current_stock": m.get("current_stock",0), "reorder_level": m.get("reorder_level",0),
                           "daily_avg": m.get("daily_consumption_avg",1), "days_remaining": fc["days_remaining"]}
        centres.append({"id": c.id, "name": c.to_dict().get("name"), "stock": stock})
    recs = compute_redistribution(centres)
    for r in recs:
        r["gemini_message"] = gemini.generate(
            f'Write a one-sentence transfer instruction: {r["quantity"]} {r["medicine"]} '
            f'from {r["from_centre"]} to {r["to_centre"]} (urgency {r["urgency"]}).', lang)
        db.collection("recommendations").add({**r, "district_id": district_id,
            "type": "REDISTRIBUTION", "status": "pending"})
    return ok({"recommendations": recs})
```

- [x] **Step 3: Add explain-underperformance** — read centre flags (recompute or stored), Gemini-explain.
```python
@router.post("/explain-underperformance/{centre_id}")
def explain(centre_id: str, lang: str = "mr", user=Depends(get_current_user)):
    from app.services.recompute import recompute_centre
    score = recompute_centre(centre_id)
    text = gemini.generate(
        f'Centre scored {score["score"]}/100. Issues: {"; ".join(score["flags"])}. '
        f'Explain in 2 sentences for a district officer and recommend one action.', lang)
    return ok({"score": score, "explanation": text})
```

- [x] **Step 4: Verify** all three via curl; confirm `/recommendations` docs appear and briefing caches (second call returns `cached:true`).

- [x] **Step 5: Commit** — `git commit -am "feat: briefing (cached), redistribution, explain endpoints"`

### Task 2.8 (FE): Dashboard UI (Claude Design against the data contract)

**Files:** Create: `web/src/pages/Dashboard.jsx` + `web/src/components/dashboard/*`; Modify: `App.jsx` (wire real Dashboard).

**Interfaces:**
- Consumes: `useCollection("centres",[where("district_id","==",id)])`, `useCollection("alerts",[where("district_id","==",id),where("resolved","==",false)])`, `api.get("/api/ai/district-briefing/...")`, `api.post("/api/ai/redistribution/...")`.

- [x] **Step 1: Generate the visual components with Claude Design.** Provide Claude Design this exact data contract and layout brief: Navbar (district name, EN/HI/MR toggle, avatar) · StatBar (total centres, critical count, beds available) · BriefingCard (text from briefing endpoint) · CentreGrid (cards: name, type, status color [operational=green, under_resourced=amber, critical=red], performance_score, top alert) · AlertsPanel (severity-sorted list) · RecoPanel (recommendation gemini_message + Acknowledge button). Live data via the hooks above; briefing/reco via `api`.

- [x] **Step 2: Wire real-time** — CentreGrid + AlertsPanel bind to `useCollection` so an operator write updates them live. Clicking a centre routes to `/centre/:id` (Task 3.1).

- [ ] **Step 3: Verify** — as admin, the dashboard shows 6 centres with correct colours, ~4 active alerts, a briefing sentence, and (after POST redistribution) recommendation cards. In a second tab as Mulshi operator, change stock → admin dashboard updates live.

- [x] **Step 4: Commit** — `git commit -am "feat: district admin dashboard (live)"`

**Day 2 gate:** Dashboard shows all 6 centres, alerts, Gemini briefing + recommendations. Operator write → live dashboard update.

---

## Phase 3 — Day 3: Complete (Centre Detail, My Centre, i18n, integration)

### Task 3.1 (FE): Centre Detail page

**Files:** Create: `web/src/pages/CentreDetail.jsx` + `components/centre/*`

**Interfaces:**
- Consumes: `api.get("/api/centres/{id}/stock")`, `/beds`, `/attendance?days=7`, `/footfall?days=30`, `/tests`, `api.post("/api/ai/explain-underperformance/{id}")`. (Add the `GET` read routes for beds/attendance/footfall/tests to `centres.py` mirroring the stock route.)

- [ ] **Step 1: Add the remaining read routes** to `app/routers/centres.py` (`/beds`, `/attendance?days=`, `/footfall?days=`, `/tests`) — each returns `ok({...})` from the matching subcollection.

- [x] **Step 2: Generate Centre Detail via Claude Design** — explanation card (from explain endpoint) · stock table with forecast progress bars + severity badges · bed occupancy RadialBarChart · 7-day attendance BarChart · 30-day footfall LineChart (annotate projection/trend from §6.4) · tests grid (✅/❌). **Cuttable:** if time-constrained, ship stock table + one chart only (Global Constraint / spec §7).

- [ ] **Step 3: Verify** — clicking PHC Velhe shows score ~38, flags, charts render from real data.

- [x] **Step 4: Commit** — `git commit -am "feat: centre detail page + read routes"`

### Task 3.2 (FE): My Centre operator page

**Files:** Create: `web/src/pages/MyCentre.jsx`; Modify: `App.jsx` (wire for `phc_operator`).

**Interfaces:**
- Consumes: operator write endpoints (Task 2.5); reads own centre via `useDoc`/`api`.

- [x] **Step 1: Generate My Centre via Claude Design** — mobile-first, scoped to `user.centre_id`: editable stock rows (number input + Save → `PATCH /stock`), beds occupied input, "log today's footfall" field, attendance (doctors present/total), test-availability toggles. Each Save calls the matching endpoint and shows a success toast.

- [ ] **Step 2: Verify the wow-path** — operator lowers paracetamol to 80 → Save → (in an admin tab) a critical alert appears within ~1s. Confirm operator cannot see other centres.

- [x] **Step 3: Commit** — `git commit -am "feat: my centre operator data-entry page"`

### Task 3.3 (FE): i18n EN/HI/MR

**Files:** Create: `web/src/i18n/translations.js`; Modify: components to use `t()`.

**Interfaces:**
- Produces: `LanguageProvider`, `useLang() -> {lang, setLang, t}`; `t(key)` resolves from the active language dict; `lang` is passed as `?lang=` to AI endpoints.

- [x] **Step 1: Write `translations.js`** with ~40 keys × {en, hi, mr} (dashboard, critical, stock_out, days_remaining, redistribute, beds, attendance, footfall, tests, acknowledge, sign_out, not_provisioned, …). Marathi default.

- [x] **Step 2: Wrap labels** in `t(key)` across Navbar/StatBar/cards/panels; wire the language toggle; append `?lang=${lang}` to briefing/forecast/redistribution/explain calls.

- [x] **Step 3: Verify** — toggling MR/HI/EN switches all static labels instantly; AI narratives return in the selected language.

- [x] **Step 4: Commit** — `git commit -am "feat: EN/HI/MR i18n"`

### Task 3.4 (Integration): Full end-to-end pass

- [ ] **Step 1: Run the whole flow** on localhost: seed → admin dashboard → operator writes at 2 centres → alerts/recommendations update live → language toggle → centre detail. Fix any envelope/CORS/claim mismatches.
- [ ] **Step 2: Run all backend tests** — `pytest -q` → all green.
- [ ] **Step 3: Commit** — `git commit -am "chore: end-to-end integration pass"`

**Day 3 gate:** Complete walkthrough with no hardcoded data; operator write → live admin alert; 3 languages working.

---

## Phase 4 — Day 4: Deploy & Harden (FEATURE FREEZE)

### Task 4.1 (IN): Dockerfile — build web, serve from FastAPI

**Files:** Create: `smart-health/api/Dockerfile`; Modify: `app/main.py` (static mount).

- [ ] **Step 1: Add static serving to `main.py`** (after routers)
```python
from fastapi.staticfiles import StaticFiles
import os
if os.path.isdir("static"):
    app.mount("/", StaticFiles(directory="static", html=True), name="static")
```

- [ ] **Step 2: Write multi-stage `Dockerfile`**
```dockerfile
FROM node:20-slim AS web
WORKDIR /web
COPY web/package*.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM python:3.11-slim
WORKDIR /app
COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY api/app ./app
COPY --from=web /web/dist ./static
ENV PORT=8080
CMD ["sh","-c","uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
```

- [ ] **Step 3: Verify locally** — `docker build -t smart-health . && docker run -p 8080:8080 --env-file api/.env smart-health`; open `localhost:8080` → app loads and API responds.

- [ ] **Step 4: Commit** — `git commit -am "feat: dockerfile serving web from fastapi"`

### Task 4.2 (IN): Deploy to Cloud Run + harden

**Files:** Create: `firestore.rules`, `firestore.indexes.json`

- [ ] **Step 1: Write `firestore.rules`** (role-scoped; operators write own centre only)
```
rules_version = '2';
service cloud.firestore {
  match /databases/{db}/documents {
    function signedIn() { return request.auth != null; }
    function role() { return request.auth.token.role; }
    function ownCentre(cid) { return request.auth.token.centre_id == cid; }

    match /districts/{d} { allow read: if signedIn(); allow write: if false; }
    match /centres/{cid} {
      allow read: if signedIn();
      allow write: if role() == 'phc_operator' && ownCentre(cid);
      match /{sub=**} {
        allow read: if signedIn();
        allow write: if role() == 'phc_operator' && ownCentre(cid);
      }
    }
    match /alerts/{a} { allow read: if signedIn(); allow write: if false; }        // backend-only via admin SDK
    match /recommendations/{r} { allow read: if signedIn(); allow write: if false; }
    match /users/{u} { allow read: if signedIn() && request.auth.uid == u; allow write: if false; }
  }
}
```
  *(Admin SDK writes from FastAPI bypass rules; rules protect direct client access.)*

- [ ] **Step 2: Write `firestore.indexes.json`** (composite for the alerts query)
```json
{ "indexes": [ { "collectionGroup": "alerts", "queryScope": "COLLECTION",
  "fields": [ {"fieldPath":"district_id","order":"ASCENDING"},
              {"fieldPath":"resolved","order":"ASCENDING"} ] } ],
  "fieldOverrides": [] }
```
  Deploy rules + indexes: `firebase deploy --only firestore:rules,firestore:indexes`.

- [ ] **Step 3: Deploy to Cloud Run** (billing must be enabled — see README setup)
```bash
gcloud run deploy smart-health --source . --region asia-south1 \
  --allow-unauthenticated --min-instances=1 \
  --set-env-vars GEMINI_MODEL=gemini-2.5-flash,SEED_ENABLED=true,ALLOWED_ORIGIN=<cloud-run-url> \
  --set-secrets GEMINI_API_KEY=gemini-key:latest
```
  (`--min-instances=1` kills cold starts during judging.)

- [ ] **Step 4: Firebase Auth config** — add the Cloud Run domain to Firebase Console → Auth → Settings → **Authorized domains**; configure the OAuth consent screen. Rebuild web with `VITE_API_BASE=<cloud-run-url>` (same origin, so `/api`).

- [ ] **Step 5: Set the ₹2,000 budget alert** (Billing → Budgets & alerts, threshold-only).

- [ ] **Step 6: Verify on the LIVE url (cold)** — open the Cloud Run URL in a fresh browser: Google Sign-In works on the live domain, dashboard loads, operator write → live alert. Test with all three demo accounts.

- [ ] **Step 7: Commit** — `git commit -am "feat: cloud run deploy + firestore rules/indexes + hardening"`

### Task 4.3 (Team): Seed live + freeze

- [ ] **Step 1: Provision live demo accounts** — each demo account signs into the live URL once (creates the Firebase user), then admin runs `POST /api/seed/district` so claims + data attach. Re-verify each account lands in the right view.
- [ ] **Step 2: Lock down** — after seeding, set `SEED_ENABLED=false` and redeploy (so `/seed/*` is disabled during judging), OR keep enabled only if you need live resets (admin-gated). Decide and document.
- [ ] **Step 3: Full team walkthrough** on the live URL. **FEATURE FREEZE.**
- [ ] **Step 4: Commit** — `git commit -am "chore: live demo seeded, feature freeze"`

---

## Phase 5 — Days 5–6: Demo, Pitch, Submit

### Task 5.1: Backup demo video (Day 5)
- [ ] Record a 3–5 min screen capture with narration: problem → operator enters stock → live alert on admin dashboard → AI briefing → redistribution recommendation → underperformance flag → language toggle. This is insurance if the live demo fails.

### Task 5.2: Pitch deck (Day 5)
- [ ] 10–12 slides: Problem (MP's PHC gap) → Solution → **live demo screenshots** → AI architecture (real algorithms + Gemini as communication layer) → Deployability (PHC operator now, e-Aushadhi/HMIS/ABDM integration + Vertex AI at scale) → Impact (Pune Rural → district → state; patients served) → Tech stack (Google Cloud) → Team. Export PDF ≤5MB.

### Task 5.3: Submission text (Day 5)
- [ ] Solution explanation ≤1000 chars (draft, trim). Technologies-used ≤1024 chars (FastAPI, React, Firestore, Firebase Auth, Cloud Run, Gemini 2.5 Flash, Recharts).
- [ ] Timed rehearsal < 5 min.

### Task 5.4: Submit (Day 6)
- [ ] Morning rehearsal on live URL; fix only blockers.
- [ ] Set GitHub repo public. Submit before 6 PM IST: Working URL · GitHub repo · solution explanation · pitch deck PDF · technologies used.

---

## Self-Review — Spec Coverage Check

| Spec requirement | Covered by |
|---|---|
| Stock monitoring + early stock-out warnings | 1.3, 1.5, 2.4 (STOCKOUT alerts) |
| AI-driven demand forecast (medicine + footfall) | 1.3 (stockout), 2.1 (footfall history), forecast_footfall §6.4 → Centre Detail 3.1 |
| Patient footfall | 2.1 (history), 2.5 (log), 3.1 (chart) |
| Bed availability | 2.1, 2.5 (beds write), 2.4 (BED_CRISIS), 3.1 (ring) |
| Doctor attendance | 2.1, 2.5 (attendance write), 2.4 (ATTENDANCE_LOW), 3.1 (chart) |
| Test availability audits | 2.1 (tests+history), 2.4 (TEST_UNAVAILABLE), 2.2 (score weight), 3.1 (grid) |
| Smart redistribution recommendations | 2.3 (engine), 2.7 (endpoint + Gemini), 2.8 (RecoPanel) |
| Flag underperforming centres | 2.2 (scoring), 2.5 (recompute), 2.7 (explain), 2.8 (status colours) |
| Real-time visibility | 1.8 (onSnapshot), 2.8 (live dashboard) |
| Multilingual (EN/HI/MR) | 3.3 + lang param on all AI endpoints |
| Auth (roles, custom claims, provisioning, fallback) | 1.2, 1.4, 1.7, 4.2 (rules) |
| Gemini off live write path | 2.4 (templates), 2.5 (recompute) |
| Google Cloud mandatory | Firestore, Firebase Auth, Cloud Run, Gemini throughout |
| Deployability (single container, min-instances, offline) | 4.1, 4.2, 0.4 (offline persistence) |
| Submission artifacts | 5.1–5.4 |

No gaps found. Types are consistent across tasks (`forecast_stockout` fields, `compute_performance_score` keys, `build_alerts` signature, `recompute_centre`, the response envelope, and the `useCollection`/`useDoc`/`api` frontend contract are referenced identically wherever consumed).
