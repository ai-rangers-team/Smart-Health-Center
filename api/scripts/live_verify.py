"""End-to-end live verification against a running local API + live Firestore.

Creates two test users (admin + operator) with custom claims, exchanges custom
tokens for real ID tokens, then drives every endpoint including the wow-path:
operator stock write -> recompute -> fresh critical alert.

Run: python -m scripts.live_verify   (uvicorn must be running on :8000)
"""
import requests
from firebase_admin import auth

from app.firestore_client import db  # noqa: F401  (initialises firebase)

API_KEY = "AIzaSyAAhHNTBlZul_WD8W23njWj5euVv1ftSo0"
BASE = "http://localhost:8000"
EXCHANGE = ("https://identitytoolkit.googleapis.com/v1/"
            f"accounts:signInWithCustomToken?key={API_KEY}")

PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("  OK  " if cond else " FAIL ") + name + (f"  [{detail}]" if detail else ""))


def id_token_for(email, claims):
    try:
        user = auth.get_user_by_email(email)
    except auth.UserNotFoundError:
        user = auth.create_user(email=email)
    auth.set_custom_user_claims(user.uid, claims)
    custom = auth.create_custom_token(user.uid)
    r = requests.post(EXCHANGE, json={"token": custom.decode(), "returnSecureToken": True})
    r.raise_for_status()
    return r.json()["idToken"]


print("minting tokens…")
admin_tok = id_token_for("test-admin@shc.demo", {
    "role": "district_admin", "district_id": "pune_rural", "centre_id": None})
op_tok = id_token_for("test-operator@shc.demo", {
    "role": "phc_operator", "district_id": "pune_rural", "centre_id": "phc_mulshi"})
A = {"Authorization": f"Bearer {admin_tok}"}
O = {"Authorization": f"Bearer {op_tok}"}

print("\n-- auth guards --")
r = requests.get(f"{BASE}/api/ai/forecast/phc_mulshi")
check("401 without token", r.status_code == 401, str(r.status_code))
r = requests.patch(f"{BASE}/api/centres/phc_haveli/stock", headers=O,
                   json={"medicine_id": "ors", "current_stock": 10})
check("403 writing another centre", r.status_code == 403, str(r.status_code))

print("\n-- AI endpoints (live Gemini) --")
# (No REST stock read — the frontend reads Firestore directly; the forecast
# endpoint returns the merged medicines + narrative.)
r = requests.get(f"{BASE}/api/ai/forecast/phc_mulshi?lang=en", headers=A).json()
meds = r["data"]["medicines"]
para = next(m for m in meds if m.get("id") == "paracetamol")
check("forecast merge: paracetamol critical", para["severity"] == "critical",
      f'{para["days_remaining"]}d')
check("ai/forecast narrative", bool(r["data"]["narrative"]),
      r["data"]["narrative"][:60])

r = requests.get(f"{BASE}/api/ai/district-briefing/pune_rural?lang=en", headers=A).json()
check("ai/district-briefing", bool(r["data"]["briefing"]), r["data"]["briefing"][:60])
r2 = requests.get(f"{BASE}/api/ai/district-briefing/pune_rural?lang=en", headers=A).json()
check("briefing cache hit", r2["data"].get("cached") is True)

r = requests.post(f"{BASE}/api/ai/redistribution/pune_rural?lang=en", headers=A).json()
recs = r["data"]["recommendations"]
check("redistribution CHC->Mulshi paracetamol",
      any(x["to_centre"] == "PHC Mulshi" and "aracetamol" in x["medicine"] for x in recs)
      or any("phc_mulshi" in str(x).lower() for x in recs),
      f"{len(recs)} recs")

r = requests.post(f"{BASE}/api/ai/explain-underperformance/phc_velhe?lang=en",
                  headers=A).json()
check("explain-underperformance", bool(r["data"]["explanation"])
      and r["data"]["score"]["score"] < 65, r["data"]["explanation"][:60])

print("\n-- WOW PATH: operator write -> recompute -> alert --")
r = requests.patch(f"{BASE}/api/centres/phc_mulshi/stock", headers=O,
                   json={"medicine_id": "paracetamol", "current_stock": 80}).json()
check("operator stock write + recompute", r["success"],
      f'status={r["data"]["recomputed"]["status"]}')

alerts = [a.to_dict() for a in db.collection("alerts")
          .where("centre_id", "==", "phc_mulshi").where("resolved", "==", False).stream()]
crit = [a for a in alerts if a["type"] == "STOCKOUT_CRITICAL"
        and a.get("medicine_name") == "Paracetamol 500mg"]
check("fresh critical alert regenerated", bool(crit),
      f'{crit[0]["days_remaining"]}d left' if crit else "none")
check("days_remaining dropped (~2d)", bool(crit) and crit[0]["days_remaining"] <= 2.5,
      str(crit[0]["days_remaining"]) if crit else "-")

print("\n-- other writes --")
for name, method, path, body in [
    ("beds", "patch", "/api/centres/phc_mulshi/beds", {"occupied": 9}),
    ("footfall", "post", "/api/centres/phc_mulshi/footfall", {"count": 85}),
    ("attendance", "post", "/api/centres/phc_mulshi/attendance",
     {"doctors_present": 1, "doctors_total": 2}),
    ("tests", "patch", "/api/centres/phc_mulshi/tests",
     {"tests": {"malaria": True, "tb": True, "pregnancy": True,
                "diabetes": True, "hiv": True}}),
]:
    r = getattr(requests, method)(f"{BASE}{path}", headers=O, json=body)
    check(f"operator {name} write", r.status_code == 200 and r.json()["success"])

print("\n-- alert resolve + recommendation acknowledge (admin) --")
alert_id = next(a.id for a in db.collection("alerts")
                .where("centre_id", "==", "phc_mulshi")
                .where("resolved", "==", False).stream())
r = requests.post(f"{BASE}/api/alerts/{alert_id}/resolve", headers=A)
check("alert resolve", r.status_code == 200 and r.json()["success"])
rec_id = next((x.id for x in db.collection("recommendations")
               .where("status", "==", "pending").stream()), None)
if rec_id:
    r = requests.post(f"{BASE}/api/recommendations/{rec_id}/acknowledge", headers=A)
    check("recommendation acknowledge", r.status_code == 200 and r.json()["success"])
r = requests.post(f"{BASE}/api/alerts/{alert_id}/resolve", headers=O)
check("operator cannot resolve alerts", r.status_code == 403, str(r.status_code))

print(f"\n==== {len(PASS)} passed, {len(FAIL)} failed ====")
if FAIL:
    print("FAILED:", FAIL)
    raise SystemExit(1)
