"""P&ID Tag Search — polished UI.

Upload P&ID PDFs -> searchable tag index -> click to highlight -> export CSV.
Run from repo root:  streamlit run src/app.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import csv
import io
import sqlite3

from PIL import Image, ImageDraw
import streamlit as st

from index import build_index, search, tag_counts

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
PDF_DIR = DATA / "samples"
DB = DATA / "index.db"
PAGES = DATA / "pages"

st.set_page_config(page_title="P&ID Tag Search", layout="wide",
                   page_icon="🏭")

# ---------- helpers ----------
def export_tag_csv(db_path: Path) -> str:
    con = sqlite3.connect(db_path)
    rows = con.execute(
        "SELECT tag, file, page, x0, y0, x1, y1 FROM tags ORDER BY file, page"
    ).fetchall()
    con.close()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["tag", "file", "page", "x0", "y0", "x1", "y1"])
    w.writerows(rows)
    return buf.getvalue()


def index_stats(db_path: Path) -> dict:
    con = sqlite3.connect(db_path)
    pdfs = con.execute("SELECT COUNT(DISTINCT file) FROM tags").fetchone()[0]
    pages = con.execute("SELECT COUNT(DISTINCT file || page) FROM tags").fetchone()[0]
    tags = con.execute("SELECT COUNT(*) FROM tags").fetchone()[0]
    uniq = con.execute("SELECT COUNT(DISTINCT tag) FROM tags").fetchone()[0]
    con.close()
    return {"pdfs": pdfs, "pages": pages, "hits": tags, "unique": uniq}


def draw_hit(png_path: str, x0, y0, x1, y1):
    img = Image.open(png_path).convert("RGB")
    d = ImageDraw.Draw(img)
    d.rectangle([x0, y0, x1, y1], outline="red", width=max(3, img.width // 400))
    return img


# ---------- sidebar ----------
with st.sidebar:
    st.header("📁 Archive")
    uploaded = st.file_uploader("Upload P&ID PDFs", type="pdf",
                                accept_multiple_files=True)
    pdf_dir = st.text_input("…or PDF folder path", str(PDF_DIR))
    if uploaded:
        up_dir = DATA / "uploads"
        up_dir.mkdir(parents=True, exist_ok=True)
        for f in uploaded:
            (up_dir / f.name).write_bytes(f.getbuffer())
        pdf_dir = str(up_dir)
        st.success(f"✅ {len(uploaded)} PDFs ready to index")
    if st.button("🔨 Build / rebuild index", use_container_width=True):
        with st.spinner("Indexing PDFs..."):
            stats = build_index(pdf_dir, DB, PAGES)
        st.success(f"{stats['pdfs']} PDFs · {stats['pages']} pages · "
                   f"{stats['tag_hits']} tag hits")
    if DB.exists():
        st.download_button("⬇️ Export tag list (CSV)", export_tag_csv(DB),
                           file_name="tag_list.csv", mime="text/csv",
                           use_container_width=True)

# ---------- header ----------
st.title("🏭 P&ID Tag Search")
st.caption("Upload P&ID PDFs → search every equipment tag → click to highlight on the drawing → export the list.")

if not DB.exists():
    st.info("👈 Build the index from the sidebar to get started.")
    st.stop()

s = index_stats(DB)
c1, c2, c3, c4 = st.columns(4)
c1.metric("PDFs", s["pdfs"])
c2.metric("Pages", s["pages"])
c3.metric("Tag hits", s["hits"])
c4.metric("Unique tags", s["unique"])
st.divider()

# ---------- search ----------
if "q" not in st.session_state:
    st.session_state.q = ""
query = st.text_input("🔍 Search tag", value=st.session_state.q,
                      placeholder="P-231   (prefix ok: P-23, wildcard: *-231)")

st.caption("Popular tags:")
top = tag_counts(DB, 12)
cols = st.columns(6)
for i, t in enumerate(top):
    if cols[i % 6].button(f"{t['tag']} ({t['n']})", key=f"pill_{t['tag']}"):
        st.session_state.q = t["tag"]
        st.rerun()
if query != st.session_state.q:
    st.session_state.q = query

q = st.session_state.q.strip()
if not q:
    st.stop()

hits = search(DB, q)
st.subheader(f"{len(hits)} hits for `{q}`")
if not hits:
    st.warning("No matches — try a prefix like `P-23` or a popular tag above.")
    st.stop()

# group by file for a cleaner result list
from collections import defaultdict
by_file = defaultdict(list)
for h in hits:
    by_file[(h["file"], h["page"])].append(h)

for (fname, page), hs in sorted(by_file.items()):
    with st.expander(f"📄 {fname} — page {page} · {len(hs)} hits", expanded=len(by_file) == 1):
        # show one image per unique tag on this page, all boxes drawn
        seen_tags = []
        for h in hs:
            if h["tag"] not in seen_tags:
                seen_tags.append(h["tag"])
        img = Image.open(hs[0]["png"]).convert("RGB")
        d = ImageDraw.Draw(img)
        for h in hs:
            d.rectangle([h["x0"], h["y0"], h["x1"], h["y1"]],
                        outline="red", width=max(3, img.width // 400))
        st.image(img, use_container_width=True,
                 caption=f"{fname} p.{page} — red boxes: {', '.join(seen_tags)}")
