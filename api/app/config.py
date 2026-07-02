from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    gemini_model: str = "gemini-2.5-flash"
    gemini_api_key: str = ""
    seed_enabled: bool = False
    allowed_origin: str = "http://localhost:5173"
    firebase_credentials_path: str = ""  # path to service-account JSON; empty = ADC


settings = Settings()
