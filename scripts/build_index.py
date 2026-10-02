"""CLI: build the tag index over a folder of P&ID PDFs.

Usage:
    python scripts/build_index.py [pdf_dir]
    python scripts/build_index.py --top 20   # most frequent tags after build
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from index import build_index, tag_counts

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf_dir", nargs="?", default=str(DATA / "samples"))
    ap.add_argument("--top", type=int, default=0,
                    help="print N most frequent tags after build")
    args = ap.parse_args()

    stats = build_index(args.pdf_dir, DATA / "index.db", DATA / "pages")
    print(f"indexed: {stats['pdfs']} PDFs, {stats['pages']} pages, "
          f"{stats['tag_hits']} tag hits -> {DATA / 'index.db'}")
    if args.top:
        for r in tag_counts(DATA / "index.db", args.top):
            print(f"  {r['tag']:12s} {r['n']}")


if __name__ == "__main__":
    main()
