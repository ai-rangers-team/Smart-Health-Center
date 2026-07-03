"""Fetch (or create) the Firebase Web App and print its config for web/.env.

Uses the Admin service account via the Firebase Management API.
Run: python -m scripts.web_config
"""
import json
import time

import google.auth.transport.requests
import requests
from google.oauth2 import service_account

from app.config import settings

PROJECT = "smart-health-a35ef"
BASE = "https://firebase.googleapis.com/v1beta1"

creds = service_account.Credentials.from_service_account_file(
    settings.firebase_credentials_path,
    scopes=["https://www.googleapis.com/auth/cloud-platform"],
)
creds.refresh(google.auth.transport.requests.Request())
H = {"Authorization": f"Bearer {creds.token}"}

apps = requests.get(f"{BASE}/projects/{PROJECT}/webApps", headers=H).json()
app_list = apps.get("apps", [])

if not app_list:
    print("no web app found — creating one…")
    op = requests.post(
        f"{BASE}/projects/{PROJECT}/webApps",
        headers=H, json={"displayName": "SHC Web"},
    ).json()
    if "error" in op:
        raise SystemExit(f"create failed: {op['error']}")
    name = op["name"]
    for _ in range(30):
        st = requests.get(f"{BASE}/{name}", headers=H).json()
        if st.get("done"):
            break
        time.sleep(2)
    apps = requests.get(f"{BASE}/projects/{PROJECT}/webApps", headers=H).json()
    app_list = apps.get("apps", [])

app_id = app_list[0]["appId"]
cfg = requests.get(f"{BASE}/projects/{PROJECT}/webApps/{app_id}/config", headers=H).json()
print(json.dumps(cfg, indent=2))
print("\n--- web/.env lines ---")
print(f"VITE_FIREBASE_API_KEY={cfg['apiKey']}")
print(f"VITE_FIREBASE_AUTH_DOMAIN={cfg.get('authDomain', PROJECT + '.firebaseapp.com')}")
print(f"VITE_FIREBASE_PROJECT_ID={cfg['projectId']}")
