"""Confirm the live Gemini model id before writing AI code (plan Task 0.2).

Run: python -m scripts.verify_gemini   (from the api/ directory, with api/.env present)
"""
import google.generativeai as genai
from app.config import settings

genai.configure(api_key=settings.gemini_api_key)

print("Flash models supporting generateContent:")
for m in genai.list_models():
    if "generateContent" in m.supported_generation_methods and "flash" in m.name:
        print(" ", m.name)

print(f"\nConfigured GEMINI_MODEL = {settings.gemini_model}")
resp = genai.GenerativeModel(settings.gemini_model).generate_content(
    "Reply with the single word: OK"
)
print("Live call response:", resp.text.strip())
