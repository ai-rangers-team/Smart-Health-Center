"""Seed the demo district directly via the Admin SDK (local/ops use).

Run: python -m scripts.seed [--reset]   (from api/, with .env + service account)
"""
import sys

from app.seed import demo_data

if "--reset" in sys.argv:
    print("wiping district data…")
    demo_data.wipe_district()

print("seeding Pune Rural District…")
results = demo_data.seed_district()
for cid, score in results.items():
    print(f"  {cid}: score={score['score']} status={score['status']} "
          f"flags={len(score['flags'])}")

accounts = demo_data.provision_accounts()
print("accounts provisioned:", accounts["provisioned"] or "none")
if accounts["skipped_never_signed_in"]:
    print("skipped (never signed in):", accounts["skipped_never_signed_in"])
print("done")
