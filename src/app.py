"""Streamlit UI: search tags across the P&ID archive, click a hit to highlight it
on the original drawing page.

Run from repo root:  streamlit run src/app.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from PIL import Image, ImageDraw
import streamlit as st

from index import build_index, search

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
PDF_DIR = DATA / "samples"
DB = DATA / "index.db"
PAGES = DATA / "pages"

st.set_page_config(page_title="P&ID Tag Search", layout="wide")
st.title("P&ID Tag Search")

with st.sidebar:
    st.header("Index")
    pdf_dir = st.text_input("PDF folder", str(PDF_DIR))
    if st.button("Build / rebuild index"):
        with st.spinner("Indexing PDFs..."):
            stats = build_index(pdf_dir, DB, PAGES)
        st.success(
            f"{stats['pdfs']} PDFs, {stats['pages']} pages, "
            f"{stats['tag_hits']} tag hits")

query = st.text_input("Search tag", placeholder="P-101   (prefix ok: P-10, wildcard: FV-*)")

if not query:
    st.info("Type a tag above — e.g. P-101 — to find every drawing and page it appears on.")
elif not DB.exists():
    st.warning("No index yet — build it from the sidebar first.")
else:
    hits = search(DB, query)
    st.write(f"**{len(hits)}** hits")
    for h in hits:
        with st.expander(f"{h['tag']} — {h['file']}  p.{h['page']}  [{h['src']}]"):
            img = Image.open(h["png"]).convert("RGB")
            d = ImageDraw.Draw(img)
            d.rectangle([h["x0"], h["y0"], h["x1"], h["y1"]],
                        outline="red", width=4)
            st.image(img,use_container_width=True)
