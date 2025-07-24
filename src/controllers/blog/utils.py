


import hashlib
import httpx
from typing import Optional

async def generate_cover_image(title: str) -> str:
    """
    Returns an Unsplash Source URL sized 1200×630 with a keyword-based photo.
    """
    # hash title to get deterministic keyword
    seed = hashlib.md5(title.encode()).hexdigest()
    keyword = title.replace(" ", "-").lower()[:30]
    url = f"https://source.unsplash.com/1200x630/?{keyword}&sig={seed}"
    # HEAD request confirms image exists
    async with httpx.AsyncClient() as client:
        r = await client.head(url)
        if r.status_code == 200:
            return str(r.url)  # final redirected URL
    # fallback
    return "https://source.unsplash.com/1200x630/?technology"



#-----------------------------------------------------------------------------
#-----------------------------------------------------------------------------


import io
import aiofiles
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

async def generate_social_card(title: str, subtitle: Optional[str] = None) -> str:
    """
    Creates a 1200×630 PNG with title text overlay, uploads to S3/CloudFront
    and returns public URL.  Here we simply save locally for demo.
    """
    W, H = 1200, 630
    base = Image.new("RGB", (W, H), "#1e293b")  # dark slate
    draw = ImageDraw.Draw(base)

    # fallback font
    try:
        font_big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 64)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 42)
    except OSError:
        font_big = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # title
    y = 200
    for line in _wrap_text(draw, title, font_big, W - 120):
        w, h = draw.textbbox((0, 0), line, font=font_big)[2:]
        draw.text(((W - w) / 2, y), line, font=font_big, fill="white")
        y += h + 20

    # optional subtitle
    if subtitle:
        y += 30
        for line in _wrap_text(draw, subtitle, font_small, W - 120):
            w, h = draw.textbbox((0, 0), line, font=font_small)[2:]
            draw.text(((W - w) / 2, y), line, font=font_small, fill="#cbd5e1")
            y += h + 15

    # save locally (replace with S3 upload in prod)
    filename = f"social_{hashlib.md5(title.encode()).hexdigest()[:8]}.png"
    buffer = io.BytesIO()
    base.save(buffer, format="PNG")
    buffer.seek(0)
    async with aiofiles.open(f"/static/{filename}", "wb") as f:
        await f.write(buffer.read())

    # return public URL
    return f"https://jobfinders.site/static/blog/images{filename}"


def _wrap_text(draw, text, font, max_width):
    """Naïve word-wrap helper."""
    words = text.split()
    lines, current = [], ""
    for w in words:
        test = f"{current} {w}".strip()
        if draw.textbbox((0, 0), test, font=font)[2] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = w
    if current:
        lines.append(current)
    return lines

