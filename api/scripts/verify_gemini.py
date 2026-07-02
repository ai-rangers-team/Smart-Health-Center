"""Confirm the live Gemini model id before writing AI code (plan Task 0.2).

Run: python -m scripts.verify_gemini   (from the api/ directory, with api/.env present)
"""
from google import genai
from app.config import settings

client = genai.Client(api_key=settings.gemini_api_key)

print("Flash models supporting generateContent:")
for m in client.models.list():
    actions = getattr(m, "supported_actions", None) or []
    if "generateContent" in actions and "flash" in m.name:
        print(" ", m.name)

print(f"\nConfigured GEMINI_MODEL = {settings.gemini_model}")
resp = client.models.generate_content(
    model=settings.gemini_model, contents="Reply with the single word: OK"
)
print("Live call response:", resp.text.strip())
