"""Append-only audit log service."""
from app.services import audit


class _Coll:
    def __init__(self):
        self.added = []

    def add(self, doc):
        self.added.append(doc)


class _DB:
    def __init__(self):
        self.colls = {}

    def collection(self, name):
        return self.colls.setdefault(name, _Coll())


def test_actor_from_user_defaults_channel_app():
    assert audit.actor_from_user({"uid": "u", "email": "e", "role": "phc_operator"}) == {
        "uid": "u", "email": "e", "role": "phc_operator", "channel": "app"}


def test_record_appends_entry_with_identity_and_before_after(monkeypatch):
    from app import firestore_client
    db = _DB()
    monkeypatch.setattr(firestore_client, "_db", db)

    audit.record("stock_update", "phc_x", "pune_rural",
                 {"uid": "u1", "email": "e", "role": "phc_operator", "channel": "app"},
                 before=120, after=90, medicine_id="paracetamol")

    entries = db.colls["audit"].added
    assert len(entries) == 1
    e = entries[0]
    assert e["action"] == "stock_update"
    assert e["centre_id"] == "phc_x" and e["district_id"] == "pune_rural"
    assert e["before"] == 120 and e["after"] == 90
    assert e["medicine_id"] == "paracetamol"
    assert e["actor"]["uid"] == "u1"
    assert "at" in e  # server timestamp sentinel


def test_record_never_raises(monkeypatch):
    from app import firestore_client

    class _BadDB:
        def collection(self, name):
            raise RuntimeError("firestore down")

    monkeypatch.setattr(firestore_client, "_db", _BadDB())
    audit.record("x", "c", "d", {}, 1, 2)  # must not raise
