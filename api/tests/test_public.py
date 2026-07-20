"""Public citizen endpoint: no auth required, and only coarse availability leaks."""


class _Doc:
    def __init__(self, doc_id, data, exists=True):
        self.id, self._data, self.exists = doc_id, data, exists

    def to_dict(self):
        return self._data


class _Query:
    def __init__(self, docs):
        self._docs = docs

    def order_by(self, *a, **k):
        return self

    def limit(self, n):
        return _Query(self._docs[:n])

    def stream(self):
        return iter(self._docs)


class _DocRef:
    def __init__(self, data):
        self._data = data

    def get(self):
        return _Doc("current", self._data)


class _Sub:
    def __init__(self, docs):
        self._docs = docs

    def document(self, _id):
        return _DocRef(self._docs.get("current", {}))

    def order_by(self, *a, **k):
        return _Query(self._docs.get("_list", []))

    def stream(self):
        return iter(self._docs.get("_list", []))


class _CentreRef:
    def __init__(self, data, subs, exists=True):
        self._data, self._subs, self._exists = data, subs, exists

    def get(self):
        return _Doc("phc_x", self._data, self._exists)

    def collection(self, name):
        return _Sub(self._subs.get(name, {}))


class _Centres:
    def __init__(self, ref):
        self._ref = ref

    def document(self, _id):
        return self._ref


class _DB:
    def __init__(self, ref):
        self._ref = ref

    def collection(self, name):
        assert name == "centres"
        return _Centres(self._ref)


def _install(monkeypatch, exists=True):
    from app import firestore_client
    ref = _CentreRef(
        {"name": "PHC X", "type": "PHC", "location": {"block": "Blk"},
         "beds_available": 3, "beds_total": 10},
        {
            "beds": {"current": {"total": 10, "available": 3}},
            "tests": {"current": {"malaria": False, "tb": True, "pregnancy": True}},
            "stock": {"_list": [
                _Doc("paracetamol", {"medicine_name": "Paracetamol 500mg",
                                     "current_stock": 120, "days_remaining": 3.0}),
                _Doc("metformin", {"medicine_name": "Metformin 500mg",
                                   "current_stock": 500, "days_remaining": 40.0}),
            ]},
            "attendance": {"_list": [_Doc("d", {"doctors_present": 1, "doctors_total": 2})]},
        },
        exists=exists,
    )
    monkeypatch.setattr(firestore_client, "_db", _DB(ref))


def _client():
    from app.main import app
    from fastapi.testclient import TestClient
    return TestClient(app)


def test_public_centre_needs_no_auth_and_returns_coarse_status(monkeypatch):
    _install(monkeypatch)
    r = _client().get("/api/public/centre/phc_x")  # no Authorization header
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["name"] == "PHC X"
    assert data["doctor_present"] is True
    assert data["beds"] == {"available": 3, "total": 10}
    assert data["tests"] == {"malaria": False, "tb": True, "pregnancy": True}
    # low-runway medicine -> "low", healthy -> "available"; NO exact counts exposed
    by_id = {m["id"]: m for m in data["medicines"]}
    assert by_id["paracetamol"]["status"] == "low"
    assert by_id["metformin"]["status"] == "available"
    assert "current_stock" not in by_id["paracetamol"]
    assert "performance_score" not in data


def test_public_centre_404_when_missing(monkeypatch):
    _install(monkeypatch, exists=False)
    r = _client().get("/api/public/centre/nope")
    assert r.status_code == 404


def test_feedback_404_when_centre_missing(monkeypatch):
    _install(monkeypatch, exists=False)
    r = _client().post("/api/public/centre/nope/feedback",
                       json={"doctor_present": False, "medicine_available": True})
    assert r.status_code == 404
