"""Tag index over SQLite: tag -> (file, page, bbox, source PNG).

Search supports exact match and prefix ("P-10" finds "P-101", "P-102"...).
"""
import sqlite3
from pathlib import Path

from ingest import render_pages, page_words, DPI
from tags import find_tags_with_boxes

SCHEMA = """
CREATE TABLE IF NOT EXISTS tags(
  tag TEXT, file TEXT, page INTEGER,
  x0 INTEGER, y0 INTEGER, x1 INTEGER, y1 INTEGER,
  png TEXT, src TEXT
);
CREATE INDEX IF NOT EXISTS idx_tags_tag ON tags(tag);
CREATE INDEX IF NOT EXISTS idx_tags_file ON tags(file, page);
"""


def build_index(pdf_dir: Path, db_path: Path, pages_dir: Path,
                dpi: int = DPI) -> dict:
    """Index every PDF in pdf_dir. Returns stats dict."""
    pdf_dir, pages_dir, db_path = Path(pdf_dir), Path(pages_dir), Path(db_path)
    if db_path.exists():
        db_path.unlink()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    con.executescript(SCHEMA)
    stats = {"pdfs": 0, "pages": 0, "tag_hits": 0}
    for pdf in sorted(pdf_dir.glob("*.pdf")):
        stats["pdfs"] += 1
        for i, (png, scale) in enumerate(render_pages(pdf, pages_dir / pdf.stem, dpi)):
            stats["pages"] += 1
            hits = find_tags_with_boxes(page_words(pdf, i, png, scale))
            con.executemany(
                "INSERT INTO tags VALUES (?,?,?,?,?,?,?,?,?)",
                [(h["tag"], pdf.name, i + 1,
                  h["x0"], h["y0"], h["x1"], h["y1"],
                  str(png), h["src"]) for h in hits])
            stats["tag_hits"] += len(hits)
    con.commit()
    con.close()
    return stats


def search(db_path: Path, query: str, limit: int = 200) -> list[dict]:
    """Exact or prefix search. Use '*' / '%' as wildcard, e.g. 'FV-*'."""
    q = (query or "").strip()
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    if not q:
        rows = []
    elif "*" in q or "%" in q:
        rows = con.execute(
            "SELECT * FROM tags WHERE tag LIKE ? ORDER BY file, page LIMIT ?",
            (q.replace("*", "%"), limit)).fetchall()
    else:
        rows = con.execute(
            "SELECT * FROM tags WHERE tag = ? OR tag LIKE ? "
            "ORDER BY file, page LIMIT ?",
            (q, q + "%", limit)).fetchall()
    con.close()
    return [dict(r) for r in rows]


def tag_counts(db_path: Path, limit: int = 50) -> list[dict]:
    """Most frequent tags in the index."""
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT tag, COUNT(*) AS n FROM tags "
        "GROUP BY tag ORDER BY n DESC LIMIT ?", (limit,)).fetchall()
    con.close()
    return [dict(r) for r in rows]
