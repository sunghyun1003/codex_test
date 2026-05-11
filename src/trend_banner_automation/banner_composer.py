from __future__ import annotations

from pathlib import Path

from .reporting import ImagePrompt


def compose_banner_with_text(
    background_path: Path,
    prompt: ImagePrompt,
    output_path: Path,
    *,
    font_path: Path = Path("C:/Windows/Fonts/malgunbd.ttf"),
) -> Path:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as exc:
        raise RuntimeError("Pillow is required to compose final banner text.") from exc

    image = Image.open(background_path).convert("RGBA")
    width, height = image.size
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    title_font = ImageFont.truetype(str(font_path), int(width * 0.075))
    sub_font = ImageFont.truetype(str(font_path), int(width * 0.038))
    cta_font = ImageFont.truetype(str(font_path), int(width * 0.043))

    margin = int(width * 0.07)
    panel_top = int(height * 0.065)
    panel_height = int(height * 0.245)
    radius = int(width * 0.045)
    draw.rounded_rectangle(
        [margin, panel_top, width - margin, panel_top + panel_height],
        radius=radius,
        fill=(255, 255, 255, 235),
    )

    title = prompt.main_copy
    sub = prompt.sub_copy or prompt.concept
    _draw_wrapped(draw, title, title_font, margin + 34, panel_top + 32, width - margin * 2 - 68, fill=(12, 46, 92, 255))
    _draw_wrapped(draw, sub, sub_font, margin + 34, panel_top + 122, width - margin * 2 - 68, fill=(58, 72, 91, 255))

    cta_h = int(height * 0.07)
    cta_y = height - int(height * 0.115)
    draw.rounded_rectangle(
        [margin, cta_y, width - margin, cta_y + cta_h],
        radius=int(cta_h * 0.5),
        fill=(16, 97, 218, 255),
    )
    cta_text = prompt.cta
    bbox = draw.textbbox((0, 0), cta_text, font=cta_font)
    draw.text(
        ((width - (bbox[2] - bbox[0])) / 2, cta_y + (cta_h - (bbox[3] - bbox[1])) / 2 - 2),
        cta_text,
        font=cta_font,
        fill=(255, 255, 255, 255),
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    Image.alpha_composite(image, overlay).convert("RGB").save(output_path, quality=95)
    return output_path


def _draw_wrapped(draw, text: str, font, x: int, y: int, max_width: int, fill) -> None:
    lines: list[str] = []
    current = ""
    for char in text:
        candidate = current + char
        bbox = draw.textbbox((0, 0), candidate, font=font)
        if bbox[2] - bbox[0] <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = char
    if current:
        lines.append(current)
    for line in lines[:2]:
        draw.text((x, y), line, font=font, fill=fill)
        y += int(font.size * 1.15)

