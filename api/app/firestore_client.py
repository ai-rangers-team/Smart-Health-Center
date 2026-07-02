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
