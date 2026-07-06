"""Restock-invoice extraction (photo/PDF -> medicine quantities).

Unlike `app.services.gemini`, which never gates a write and swallows every
error into "", this module feeds a review screen that pre-fills the
operator's stock form (see api/app/routers/operator.py's `/stock/extract`).
A silent failure here would just look like nothing happened, so exceptions
propagate — the caller turns them into a 502 the operator can act on (retry
or fall back to manual entry).
"""
from typing import Literal

from google.genai import types
from pydantic import BaseModel

from app.services.gemini import _get_client
from app.config import settings


class ExtractedItem(BaseModel):
    raw_name: str
    medicine_id: str | None = None
    quantity: float
    confidence: Literal["high", "medium", "low"] = "medium"


def extract_restock_items(file_bytes: bytes, mime_type: str, catalog: list[dict]) -> list[ExtractedItem]:
    """catalog: [{id, name, unit}, ...] — the centre's own medicine catalog,
    so Gemini only matches against medicines this centre actually stocks."""
    catalog_lines = "\n".join(f'- {c["id"]}: {c["name"]} ({c["unit"]})' for c in catalog)
    prompt = (
        "You are reading a medicine supply/restock invoice or delivery note for a "
        "rural health centre in India. The centre's medicine catalog (id: name (unit)) is:\n"
        f"{catalog_lines}\n\n"
        "For every line item in the document that lists a medicine and a quantity "
        "received, output one entry with: raw_name (the item name exactly as printed), "
        "medicine_id (the matching catalog id above, or null if you are not confident it "
        "matches any catalog medicine), quantity (the numeric quantity received — ignore "
        "price, amount, and batch/expiry columns), and confidence (high/medium/low, based "
        "on how certain the catalog match is). Ignore non-medicine line items entirely "
        "(gloves, syringes, delivery charges, taxes, totals)."
    )
    resp = _get_client().models.generate_content(
        model=settings.gemini_model,
        contents=[prompt, types.Part.from_bytes(data=file_bytes, mime_type=mime_type)],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=list[ExtractedItem],
        ),
    )
    return resp.parsed or []
