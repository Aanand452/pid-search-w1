# P&ID Tag Search — Weekend 1

Upload a folder of P&ID PDFs → searchable tag index → click a hit, see the tag
highlighted on the original drawing. No ML — embedded text first, OCR fallback.

## Setup

```bash
# system dep for scanned pages (skip if all your PDFs are vector)
sudo apt install tesseract-ocr

python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# sample data: 10 public P&IDs (DiagEx repro package, Apache-2.0)
bash scripts/download_samples.sh
```

## Run

```bash
# build the index
python scripts/build_index.py                 # uses data/samples/
python scripts/build_index.py /path/to/pdfs   # or your own folder
python scripts/build_index.py --top 20        # + most frequent tags

# search UI
streamlit run src/app.py
```

Demo target: type `P-101` → every drawing/page listed → click → red box on the tag.

## How it works

1. **ingest.py** — PyMuPDF renders each page to PNG @200dpi. Words + boxes come
   from embedded PDF text (pdfplumber) when present, else Tesseract OCR.
2. **tags.py** — regex `\b[A-Z]{1,4}-\d{3,5}[A-Z]?\b` catches P-101, LT-204,
   FV-301A… (ISA-5.1-ish).
3. **index.py** — SQLite: `tag -> (file, page, bbox, png)`. Exact + prefix search.
4. **app.py** — Streamlit: search box, expandable hits, bbox overlay.

## What's next (W2)

Symbol detection (boxes for pumps/valves/vessels, not just text tags) using the
AWS open-source P&ID pipeline's pre-trained model, overlaid on the same pages.
Every drafter correction gets logged as structured training data
(model version + timestamp) — that log is the future corpus.
