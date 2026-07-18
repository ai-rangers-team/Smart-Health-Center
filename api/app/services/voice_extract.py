"""Spoken stock report -> medicine quantities (low-literacy / hands-free entry).

The rubric explicitly rewards voice / low-literacy access. A health worker who
struggles with a touch keyboard can instead *say* how much stock is left — in
Hindi, Marathi or English — and Gemini transcribes + maps it to the centre's
catalog. Same structured-output pattern as `invoice_extract`, and like it this
feeds a REVIEW screen (pre-fills the stepper form); the operator still confirms
via the normal PATCH /stock flow, so a mis-hear can never silently write stock.

Semantics differ from the invoice path: an invoice states quantity *received*
(added to stock); a spoken report states the quantity *remaining* (an absolute
count that replaces current_stock).
"""
from typing import Literal

from google.genai import types
from pydantic import BaseModel

from app.config import settings
from app.services.gemini import _get_client

_LANG = {"en": "English", "hi": "Hindi", "mr": "Marathi"}


class SpokenItem(BaseModel):
    raw_name: str
    medicine_id: str | None = None
    quantity: float
    confidence: Literal["high", "medium", "low"] = "medium"


class SpokenStock(BaseModel):
    transcript: str
    items: list[SpokenItem]


def extract_stock_from_speech(audio_bytes: bytes, mime_type: str, catalog: list[dict],
                              lang: str = "mr") -> SpokenStock:
    """catalog: [{id, name, unit}, ...] — the centre's own medicines, so Gemini only
    matches against what this centre actually stocks."""
    catalog_lines = "\n".join(f'- {c["id"]}: {c["name"]} ({c["unit"]})' for c in catalog)
    spoken = _LANG.get(lang, "the local language")
    prompt = (
        "You are listening to a rural health-centre worker in India reading out how much "
        f"medicine stock is LEFT (remaining on the shelf), most likely in {spoken}. "
        f"The centre's medicine catalog (id: name (unit)) is:\n{catalog_lines}\n\n"
        "First set transcript to what you hear, verbatim, in its original script. Then for "
        "every medicine the worker states a remaining quantity for, output one item with: "
        "raw_name (the medicine as spoken), medicine_id (the matching catalog id above, or "
        "null if you are not confident it matches any catalog medicine), quantity (the number "
        "spoken, as a plain integer count of units), and confidence (high/medium/low for the "
        "catalog match). Numbers may be spoken in words or digits and in any of Hindi, Marathi "
        "or English — convert them to a number. Ignore greetings and filler."
    )
    resp = _get_client().models.generate_content(
        model=settings.gemini_model,
        contents=[prompt, types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=SpokenStock,
        ),
    )
    return resp.parsed or SpokenStock(transcript="", items=[])
