"""Tag extraction: ISA-5.1-ish instrument/equipment tag patterns.

Matches tags like: P-101, LT-204, FV-301A, XV-1001, PIC-204B
Pattern: 1-4 uppercase letters, hyphen, 3-5 digits, optional trailing letter.
"""
import re

TAG_RE = re.compile(r"\b[A-Z]{1,4}-\d{3,5}[A-Z]?\b")


def find_tags_in_text(text: str) -> list[str]:
    """Unique tags in a blob of text (no boxes)."""
    return sorted(set(TAG_RE.findall(text)))


def find_tags_with_boxes(words: list[dict]) -> list[dict]:
    """Match OCR/embedded words against the tag pattern, keep bboxes.

    Returns: [{tag, x0, y0, x1, y1, src}, ...] deduplicated.
    """
    hits = []
    for w in words:
        for m in TAG_RE.findall(w["text"]):
            hits.append({
                "tag": m,
                "x0": w["x0"], "y0": w["y0"],
                "x1": w["x1"], "y1": w["y1"],
                "src": w.get("src", ""),
            })
    seen, out = set(), []
    for h in hits:
        k = (h["tag"], h["x0"], h["y0"], h["x1"], h["y1"])
        if k not in seen:
            seen.add(k)
            out.append(h)
    return out
