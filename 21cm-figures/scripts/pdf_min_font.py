#!/usr/bin/env python3
"""Report the font sizes actually printed in a PDF.

Checks figures (and foldouts, posters, generated tables) at their final size:
run it on the built document, not on the figure file, because LaTeX's scaling
changes the printed size. Needs PyMuPDF (``import fitz``).

    python pdf_min_font.py memo-008.pdf                  # smallest size per page
    python pdf_min_font.py paper.pdf --pages 3-5 --below 8   # list text under 8 pt

Text inside raster images is invisible to this check; look at those by eye.
Exits 1 if --below is given and any text is smaller.
"""
import argparse
import collections
import sys

import fitz


def parse_pages(spec, n):
    if not spec:
        return range(1, n + 1)
    pages = set()
    for part in spec.split(","):
        lo, _, hi = part.strip().partition("-")
        pages.update(range(int(lo), int(hi or lo) + 1))
    return sorted(p for p in pages if 1 <= p <= n)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("pdf")
    ap.add_argument("--pages", help="1-based pages, e.g. 3-5,9")
    ap.add_argument("--below", type=float, help="list every span smaller than this (pt)")
    args = ap.parse_args()

    doc = fitz.open(args.pdf)
    small = []
    overall = collections.Counter()
    for p in parse_pages(args.pages, doc.page_count):
        sizes = collections.Counter()
        for block in doc[p - 1].get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                for span in line["spans"]:
                    text = span["text"].strip()
                    if not text:
                        continue
                    size = round(span["size"], 1)
                    sizes[size] += len(text)
                    if args.below is not None and size < args.below:
                        small.append((p, size, text))
        if sizes:
            overall.update(sizes)
            print(f"page {p:4d}: min {min(sizes):5.1f} pt, most text at {sizes.most_common(1)[0][0]:.1f} pt")
    if overall:
        print(f"document: min {min(overall):.1f} pt")
    if args.below is not None:
        for p, size, text in small:
            print(f"  p{p} {size:.1f} pt: {text[:70]}")
        print(f"{len(small)} span(s) below {args.below} pt")
        return 1 if small else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
