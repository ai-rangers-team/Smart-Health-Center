from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    gemini_model: str = "gemini-2.5-flash"
    gemini_api_key: str = ""          # if empty, Gemini uses Vertex AI via the service account
    gemini_location: str = "global"   # Vertex AI region for Gemini (e.g. global, us-central1)
    seed_enabled: bool = False
    allowed_origin: str = "http://localhost:5173"
    firebase_credentials_path: str = ""  # path to service-account JSON; empty = ADC
    # Shared secret an SMS/WhatsApp gateway (or the demo simulator) presents to the
    # write webhook. Default is a demo value so it works out of the box; set a strong
    # value in production, where a real gateway — not the public simulator — sends it.
    sms_webhook_secret: str = "demo-sms"


settings = Settings()
