from __future__ import annotations

import base64
import time
from pathlib import Path

from .config import Settings


class OpenAIUnavailable(RuntimeError):
    pass


def _client(settings: Settings):
    if not settings.openai_api_key:
        raise OpenAIUnavailable("OPENAI_API_KEY is not configured.")
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise OpenAIUnavailable("The openai Python package is not installed.") from exc
    return OpenAI(api_key=settings.openai_api_key)


def generate_report(settings: Settings, prompt: str, source_brief: str) -> str:
    client = _client(settings)
    response = client.responses.create(
        model=settings.openai_text_model,
        input=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": source_brief},
        ],
    )
    output_text = getattr(response, "output_text", None)
    if output_text:
        return output_text

    chunks: list[str] = []
    for item in getattr(response, "output", []) or []:
        for content in getattr(item, "content", []) or []:
            text = getattr(content, "text", None)
            if text:
                chunks.append(text)
    if not chunks:
        raise OpenAIUnavailable("OpenAI response did not include text output.")
    return "\n".join(chunks)


def generate_image(settings: Settings, prompt: str, output_path: Path) -> Path:
    client = _client(settings)
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            response = client.images.generate(
                model=settings.openai_image_model,
                prompt=prompt,
                size=settings.openai_image_size,
                n=1,
            )
            break
        except Exception as exc:  # noqa: BLE001 - rate limits should be retried politely
            last_error = exc
            if attempt == 2:
                raise
            time.sleep(60 * (attempt + 1))
    else:
        raise OpenAIUnavailable(f"Image generation failed: {last_error}")
    image_data = response.data[0]
    b64_json = getattr(image_data, "b64_json", None)
    if not b64_json:
        raise OpenAIUnavailable("Image response did not include base64 data.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(base64.b64decode(b64_json))
    return output_path
