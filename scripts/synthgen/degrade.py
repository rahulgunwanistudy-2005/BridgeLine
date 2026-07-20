"""Parameterized, deterministic degradation of rendered IEP PDFs into messy scans.

Rasterizes a clean PDF (pymupdf, build-time), applies degradations with Pillow/NumPy under
a fixed seed, and returns page images that ``pdf.build_image_pdf`` wraps into an image-only
"scanned" PDF. Every effect is scaled by ``DegradeParams`` so the teammate can request
harder or easier variants while tuning. Given pinned Pillow/NumPy/pymupdf and a fixed seed,
output is byte-stable.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFont

try:  # pymupdf is a build-time tool; import lazily-friendly
    import fitz
except ImportError:  # pragma: no cover
    fitz = None  # type: ignore[assignment]

WHITE = 255
RASTER_DPI = 150


@dataclass(frozen=True)
class DegradeParams:
    """Intensity knobs. `scale` multiplies every effect for harder/easier variants."""

    scale: float = 1.0
    rotation_deg: float = 3.0
    noise_sigma: float = 16.0
    contrast_factor: float = 0.82
    brightness_factor: float = 1.06
    jpeg_quality: int = 78
    dpi: int = RASTER_DPI

    @classmethod
    def preset(cls, name: str) -> DegradeParams:
        presets = {
            "light": cls(scale=0.5, rotation_deg=1.5, noise_sigma=8.0,
                         contrast_factor=0.9, jpeg_quality=88),
            "medium": cls(),
            "heavy": cls(scale=1.6, rotation_deg=3.0, noise_sigma=26.0,
                         contrast_factor=0.72, brightness_factor=1.12, jpeg_quality=62),
        }
        if name not in presets:
            raise ValueError(f"unknown intensity preset: {name}")
        return presets[name]


def rasterize_pdf(pdf_bytes: bytes, dpi: int = RASTER_DPI) -> list[Image.Image]:
    """Render each PDF page to an RGB PIL image."""

    if fitz is None:
        raise RuntimeError("pymupdf (fitz) is required to rasterize PDFs; see scripts/requirements.txt")
    images: list[Image.Image] = []
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for page in doc:
            pix = page.get_pixmap(dpi=dpi, alpha=False)
            images.append(Image.frombytes("RGB", (pix.width, pix.height), pix.samples))
    return images


def _font(size: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # very old Pillow without size arg
        return ImageFont.load_default()


# ── primitives ───────────────────────────────────────────────────────────────
def add_gaussian_noise(img: Image.Image, sigma: float, rng: np.random.Generator) -> Image.Image:
    arr = np.asarray(img).astype(np.float32)
    noise = rng.normal(0.0, sigma, arr.shape).astype(np.float32)
    return Image.fromarray(np.clip(arr + noise, 0, 255).astype(np.uint8), img.mode)


def rotate(img: Image.Image, deg: float) -> Image.Image:
    return img.rotate(deg, resample=Image.BICUBIC, expand=False, fillcolor=WHITE)


def contrast_drift(img: Image.Image, contrast: float, brightness: float) -> Image.Image:
    img = ImageEnhance.Contrast(img).enhance(contrast)
    return ImageEnhance.Brightness(img).enhance(brightness)


def _wobble_line(draw: ImageDraw.ImageDraw, x0, y0, x1, y1, rng, color, width, jitter=2.5):
    steps = max(6, int(abs(x1 - x0) / 24) + 1)
    pts = []
    for i in range(steps + 1):
        t = i / steps
        x = x0 + (x1 - x0) * t + rng.normal(0, jitter)
        y = y0 + (y1 - y0) * t + rng.normal(0, jitter)
        pts.append((x, y))
    draw.line(pts, fill=color, width=width, joint="curve")


def add_handwriting(img: Image.Image, rng: np.random.Generator) -> Image.Image:
    img = img.convert("RGB")
    draw = ImageDraw.Draw(img)
    w, h = img.size
    ink = (20, 40, 130)  # blue pen
    font = _font(int(h * 0.018))
    # Margin annotation on the right.
    draw.text((int(w * 0.80), int(h * 0.24)), "review\nw/ parent", fill=ink, font=font, spacing=3)
    _wobble_line(draw, int(w * 0.79), int(h * 0.30), int(w * 0.90), int(h * 0.30), rng, ink, 2)
    # A margin note lower down with an arrow.
    draw.text((int(w * 0.05), int(h * 0.55)), "check minutes", fill=ink, font=font)
    _wobble_line(draw, int(w * 0.20), int(h * 0.565), int(w * 0.32), int(h * 0.60), rng, ink, 2)
    # Crossed-out line through a line of body text.
    y = int(h * 0.63)
    _wobble_line(draw, int(w * 0.08), y, int(w * 0.72), y, rng, (150, 20, 20), 3, jitter=1.5)
    return img


def add_stamp_and_signature(img: Image.Image, rng: np.random.Generator) -> Image.Image:
    img = img.convert("RGB")
    w, h = img.size
    # Circular "RECEIVED" stamp on a transparent layer, rotated, overlapping printed text.
    stamp = Image.new("RGBA", (int(w * 0.26), int(w * 0.26)), (0, 0, 0, 0))
    sd = ImageDraw.Draw(stamp)
    red = (176, 30, 30, 190)
    sw, sh = stamp.size
    sd.ellipse([6, 6, sw - 6, sh - 6], outline=red, width=5)
    sd.ellipse([16, 16, sw - 16, sh - 16], outline=red, width=2)
    sfont = _font(int(sw * 0.12))
    sd.text((sw * 0.5, sh * 0.36), "RIVERSIDE DEMO", fill=red, font=sfont, anchor="mm")
    sd.text((sw * 0.5, sh * 0.52), "RECEIVED", fill=red, font=_font(int(sw * 0.16)), anchor="mm")
    sd.text((sw * 0.5, sh * 0.66), "2026-11-05", fill=red, font=sfont, anchor="mm")
    stamp = stamp.rotate(-18 + float(rng.normal(0, 3)), resample=Image.BICUBIC, expand=True)
    img.paste(stamp, (int(w * 0.55), int(h * 0.30)), stamp)
    # Signature squiggle overlapping the signature line area.
    draw = ImageDraw.Draw(img)
    blue = (25, 40, 120)
    base_x, base_y = int(w * 0.12), int(h * 0.86)
    pts = []
    for i in range(40):
        t = i / 39
        x = base_x + t * (w * 0.28)
        y = base_y + np.sin(t * 9) * (h * 0.02) + rng.normal(0, 2)
        pts.append((x, y))
    draw.line(pts, fill=blue, width=3, joint="curve")
    return img


def print_scan(img: Image.Image, params: DegradeParams, rng: np.random.Generator,
               *, deg: float | None = None) -> Image.Image:
    """The core print→scan look: grayscale, rotate, contrast drift, gaussian noise."""

    s = params.scale
    img = img.convert("L")
    angle = (params.rotation_deg if deg is None else deg) * (1 if rng.random() > 0.5 else -1)
    img = rotate(img, angle * s if deg is None else deg)
    img = contrast_drift(img, 1 - (1 - params.contrast_factor) * s, params.brightness_factor)
    img = add_gaussian_noise(img, params.noise_sigma * s, rng)
    return img
