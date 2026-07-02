from app import firestore_client


def test_verify_id_token_delegates_to_firebase_auth(monkeypatch):
    calls = {}

    def fake_verify(token):
        calls["token"] = token
        return {"uid": "u1", "email": "a@b.com"}

    monkeypatch.setattr(firestore_client.auth, "verify_id_token", fake_verify)
    result = firestore_client.verify_id_token("sometoken")

    assert calls["token"] == "sometoken"
    assert result == {"uid": "u1", "email": "a@b.com"}
