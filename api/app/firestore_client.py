import firebase_admin
from firebase_admin import credentials, firestore, auth
from app.config import settings

_db = None


def _init_app():
    if not firebase_admin._apps:
        cred = (credentials.Certificate(settings.firebase_credentials_path)
                if settings.firebase_credentials_path else credentials.ApplicationDefault())
        firebase_admin.initialize_app(cred)


def _get_db():
    # Lazy: firestore.client() resolves ADC immediately, which would crash any
    # import of this module before real credentials are configured — e.g. on a
    # fresh checkout, in CI, or for the auth-guard unit tests.
    global _db
    if _db is None:
        _init_app()
        _db = firestore.client()
    return _db


def __getattr__(name):
    # PEP 562 module-level lazy attribute: `from app.firestore_client import db`
    # only builds the Firestore client the first time `db` is actually accessed.
    if name == "db":
        return _get_db()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def verify_id_token(token: str) -> dict:
    _init_app()
    return auth.verify_id_token(token)
