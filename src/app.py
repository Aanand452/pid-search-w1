"""PidPilot — your P&ID copilot.

Upload P&ID PDFs -> searchable tag index -> click to highlight -> export CSV.
Run from repo root:  streamlit run src/app.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import csv
import io
import sqlite3
from collections import defaultdict

from PIL import Image, ImageDraw
import streamlit as st

from index import build_index, search, tag_counts

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
PDF_DIR = DATA / "samples"
DB = DATA / "index.db"
PAGES = DATA / "pages"
LOGO = ROOT / "assets" / "pidpilot-logo.webp"

NAVY, ORANGE, BG = "#0F1B2D", "#FF6B2C", "#F6F8FB"

st.set_page_config(page_title="PidPilot", layout="wide", page_icon="🏭")

st.markdown(f"""
<style>
#MainMenu {{visibility: hidden;}}
footer {{visibility: hidden;}}
header[data-testid="stHeader"] {{display: none;}}
.stApp {{background-color: {BG};}}

/* ---------- sidebar ---------- */
[data-testid="stSidebar"] {{background-color: {NAVY};}}
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3, [data-testid="stSidebar"] p,
[data-testid="stSidebar"] label, [data-testid="stSidebar"] span {{
    color: #E8EEF5 !important;}}
[data-testid="stSidebar"] .stTextInput input {{
    background-color: #1B2A44; color: #fff;
    border: 1px solid #2E4468; border-radius: 8px;}}
[data-testid="stSidebar"] .stButton > button {{
    background-color: {ORANGE}; color: #fff; border: none;
    border-radius: 8px; font-weight: 700; width: 100%;}}
[data-testid="stSidebar"] .stButton > button:hover {{
    background-color: #E55A1F; color: #fff;}}
[data-testid="stSidebar"] .stDownloadButton > button {{
    background-color: transparent; color: #E8EEF5;
    border: 1px solid #2E4468; border-radius: 8px; width: 100%;}}
[data-testid="stSidebar"] [data-testid="stFileUploader"] {{
    background-color: #1B2A44; border-radius: 8px; padding: 8px;}}

/* ---------- main ---------- */
h1 {{color: {NAVY} !important; font-weight: 800; letter-spacing: -0.5px;}}
.stTextInput > div > div > input {{
    border-radius: 10px; border: 1.5px solid #D5DDE8;
    padding: 12px 14px; font-size: 16px;}}
.stTextInput > div > div > input:focus {{
    border-color: {ORANGE}; box-shadow: 0 0 0 3px rgba(255,107,44,.15);}}
[data-testid="stMetricValue"] {{color: {NAVY};}}
.stButton > button {{
    border-radius: 8px; border: 1px solid #D5DDE8;
    background: #fff; font-weight: 600;}}
.stButton > button:hover {{border-color: {ORANGE}; color: {ORANGE};}}
[data-testid="stExpander"] {{
    background: #fff; border-radius: 10px;
    border: 1px solid #E4E9F0 !important;}}
.hero-sub {{color: #5A6B85; font-size: 17px; margin-top: -12px;}}
.pill-label {{color: #5A6B85; font-size: 13px; margin: 14px 0 6px;}}
</style>
""", unsafe_allow_html=True)


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


# ---------- sidebar ----------
with st.sidebar:
    if LOGO.exists():
        c1, c2, c3 = st.columns([1, 2, 1])
        c2.image(str(LOGO), use_container_width=True)
    st.markdown("<h2 style='text-align:center;'>PidPilot</h2>",
                unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:#8FA1BC !important;'>"
                "P&ID copilot for drafters</p>", unsafe_allow_html=True)
    st.divider()
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
    if st.button("🔨 Build index"):
        with st.spinner("Indexing PDFs…"):
            stats = build_index(pdf_dir, DB, PAGES)
        st.success(f"{stats['pdfs']} PDFs · {stats['pages']} pages · "
                   f"{stats['tag_hits']} tags")
    if DB.exists():
        st.download_button("⬇️ Export tag list (CSV)", export_tag_csv(DB),
                           file_name="pidpilot_tags.csv", mime="text/csv")

# ---------- hero ----------
h1, h2 = st.columns([1, 9])
if LOGO.exists():
    h1.image(str(LOGO), width=72)
h2.markdown("# PidPilot")
st.markdown("<p class='hero-sub'>Search every equipment tag across your P&ID "
            "archive. Click a hit to see it on the drawing. Export the list.</p>",
            unsafe_allow_html=True)

if not DB.exists():
    st.info("👈 Upload PDFs and build the index from the sidebar to get started.")
    st.stop()

s = index_stats(DB)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Drawings", s["pdfs"])
c2.metric("Pages", s["pages"])
c3.metric("Tag hits", s["hits"])
c4.metric("Unique tags", s["unique"])
st.divider()

# ---------- search ----------
if "q" not in st.session_state:
    st.session_state.q = ""
query = st.text_input("Search", value=st.session_state.q, label_visibility="collapsed",
                      placeholder="🔍  Try P-231 …  (prefix ok: P-23, wildcard: *-231)")

st.markdown("<p class='pill-label'>POPULAR TAGS</p>", unsafe_allow_html=True)
top = tag_counts(DB, 12)
cols = st.columns(6)
for i, t in enumerate(top):
    if cols[i % 6].button(f"{t['tag']} · {t['n']}", key=f"pill_{t['tag']}"):
        st.session_state.q = t["tag"]
        st.rerun()
if query != st.session_state.q:
    st.session_state.q = query

q = st.session_state.q.strip()
if not q:
    st.stop()

hits = search(DB, q)
st.subheader(f"{len(hits)} hits for “{q}”")
if not hits:
    st.warning("No matches — try a prefix like P-23 or a popular tag above.")
    st.stop()

by_file = defaultdict(list)
for h in hits:
    by_file[(h["file"], h["page"])].append(h)

for (fname, page), hs in sorted(by_file.items()):
    with st.expander(f"📄 {fname}  ·  page {page}  ·  {len(hs)} hits",
                     expanded=len(by_file) == 1):
        img = Image.open(hs[0]["png"]).convert("RGB")
        d = ImageDraw.Draw(img)
        for h in hs:
            d.rectangle([h["x0"], h["y0"], h["x1"], h["y1"]],
                        outline="#FF2C2C", width=max(4, img.width // 350))
        tags_here = sorted({h["tag"] for h in hs})
        st.image(img, use_container_width=True,
                 caption=f"{', '.join(tags_here)}")
