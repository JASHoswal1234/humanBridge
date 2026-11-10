"""Real multimodal AI extraction plus transparent (not calibrated) escalation rules."""
import io
import json
import os
from decimal import Decimal, InvalidOperation
from typing import Optional

from PIL import Image
from pydantic import BaseModel


class ExtractedReceipt(BaseModel):
    merchant: Optional[str] = None
    date: Optional[str] = None
    subtotal: Optional[str] = None
    tax: Optional[str] = None
    total: Optional[str] = None


def read_receipt(image_bytes: bytes, mime: str) -> tuple[dict, dict]:
    """Two distinct Gemini readings, intentionally *not* treated as independent or calibrated."""
    api_key = os.getenv('GEMINI_API_KEY', '').strip()
    if not api_key:
        raise RuntimeError('GEMINI_API_KEY is not configured. Use Demo Batch to explore simulated outputs.')
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    model = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')
    img_part = types.Part.from_bytes(data=image_bytes, mime_type=mime)
    prompts = [
        'Read the receipt carefully. Return the printed merchant, date, subtotal, tax and total. '
        'Preserve amounts exactly as printed. Null if illegible. Never calculate missing fields.',
        'Independently transcribe the visible receipt in a structured form. '
        'Inspect the bottom line carefully. Null if an amount cannot be read; do not guess.',
    ]
    outputs = []
    for prompt in prompts:
        response = client.models.generate_content(
            model=model,
            contents=[prompt, img_part],
            config=types.GenerateContentConfig(
                response_mime_type='application/json',
                response_schema=ExtractedReceipt,
                temperature=0,
            ),
        )
        parsed = response.parsed
        if parsed is not None:
            outputs.append(parsed.model_dump())
        else:
            outputs.append(ExtractedReceipt.model_validate(json.loads(response.text)).model_dump())
    return outputs[0], outputs[1]


def decimal_value(value: Optional[str]) -> Optional[Decimal]:
    if value is None or not str(value).strip():
        return None
    cleaned = str(value).strip().replace('$', '').replace('₹', '').replace(',', '').replace('USD', '')
    try:
        return Decimal(cleaned).quantize(Decimal('0.01'))
    except (InvalidOperation, ValueError):
        return None


def analyze(first: dict, second: dict) -> tuple[bool, list[str]]:
    reasons = []
    a = decimal_value(first.get('total'))
    b = decimal_value(second.get('total'))
    if a is None or b is None:
        reasons.append('Missing or unreadable total')
    elif a != b:
        reasons.append('Two AI readings disagree on total')
    subtotal = decimal_value(first.get('subtotal'))
    tax = decimal_value(first.get('tax'))
    if a is not None and subtotal is not None and tax is not None:
        if abs((subtotal + tax) - a) > Decimal('0.02'):
            reasons.append('Subtotal + tax does not equal total')
    if a is not None and a <= 0:
        reasons.append('Non-positive receipt total')
    return bool(reasons), reasons


def crop_receipt(image_bytes: bytes) -> bytes:
    """MVP crop heuristic: bottom half, NOT a privacy or PII guarantee."""
    with Image.open(io.BytesIO(image_bytes)) as image:
        image = image.convert('RGB')
        w, h = image.size
        crop = image.crop((0, int(h * .46), w, h))
        output = io.BytesIO()
        crop.save(output, format='PNG')
        return output.getvalue()
