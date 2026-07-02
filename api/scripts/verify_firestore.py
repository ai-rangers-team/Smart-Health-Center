from app.firestore_client import db

doc_ref = db.collection("_ping").document("test")
doc_ref.set({"hello": "world"})
snap = doc_ref.get()
print("round-trip read:", snap.to_dict())
assert snap.to_dict() == {"hello": "world"}, "round-trip mismatch"
doc_ref.delete()
print("OK — Firestore round-trip verified, cleaned up")
