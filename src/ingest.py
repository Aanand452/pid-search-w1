"""PDF ingestion: render pages to PNG, extract words with bounding boxes.

Strategy per page:
1. Try embedded text via pdfplumber (vector PDFs) -> word boxes in PDF points,
   scaled to PNG pixels.
2. If too few words -> Tesseract OCR on the rendered PNG (boxes already pixels).
"""
from pathlib import Path

import pymupdf
import pdfplumber
from PIL import Image
import pytesseract

DPI = 200
MIN_EMBEDDED_WORDS = 5


def render_pages(pdf_path: Path, out_dir: Path, dpi: int = DPI,
                 max_px: int = 5000) -> list[tuple[Path, float]]:
    """Render every page to PNG. Returns [(png_path, scale)] where scale is
    pixels per PDF point actually used (capped so huge A1 sheets don't blow
    up memory)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open(pdf_path)
    out = []
    for i, page in enumerate(doc):
        w, h = page.rect.width, page.rect.height
        zoom = min(dpi / 72.0, max_px / max(w, h))
        pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))
        p = out_dir / f"page-{i + 1:03d}.png"
        pix.save(p)
        out.append((p, zoom))
    doc.close()
    return out


def _plumber_words(pdf_path: Path, page_idx: int, scale: float) -> list[dict]:
    """Word boxes from embedded PDF text, converted to PNG pixel coords."""
    with pdfplumber.open(pdf_path) as pdf:
        raw = pdf.pages[page_idx].extract_words() or []
    out = []
    for w in raw:
        t = (w.get("text") or "").strip()
        if t:
            out.append({
                "text": t,
                "x0": int(w["x0"] * scale), "y0": int(w["top"] * scale),
                "x1": int(w["x1"] * scale), "y1": int(w["bottom"] * scale),
                "src": "embedded",
            })
    return out


def _ocr_words(png_path: Path) -> list[dict]:
    """Word boxes via Tesseract OCR (for scanned pages)."""
    try:
        data = pytesseract.image_to_data(
            Image.open(png_path), output_type=pytesseract.Output.DICT)
    except Exception as e:  # tesseract binary missing etc.
        print(f"  [warn] OCR skipped for {png_path.name}: {e}")
        return []
    out = []
    for i, t in enumerate(data["text"]):
        t = (t or "").strip()
        if not t:
            continue
        try:
            conf = float(data["conf"][i])
        except (ValueError, TypeError):
            conf = -1.0
        if conf < 30:  # drop low-confidence junk
            continue
        out.append({
            "text": t,
            "x0": data["left"][i], "y0": data["top"][i],
            "x1": data["left"][i] + data["width"][i],
            "y1": data["top"][i] + data["height"][i],
            "src": "ocr",
        })
    return out


def page_words(pdf_path: Path, page_idx: int, png_path: Path,
               scale: float) -> list[dict]:
    """Words + pixel bboxes for one page. Embedded text first, OCR fallback."""
    words = _plumber_words(pdf_path, page_idx, scale)
    if len(words) >= MIN_EMBEDDED_WORDS:
        return words
    return _ocr_words(png_path)
