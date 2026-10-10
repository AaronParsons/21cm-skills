#!/usr/bin/env python3
"""Find short final lines of paragraphs in a rendered PDF and estimate the trim.

Reads the PDF's geometry, not the LaTeX source's line breaks. A candidate is a
paragraph whose last printed line holds only a few words; shortening the
paragraph by roughly the reported width pulls that line up and saves a line.
Estimates are approximate: TeX re-breaks the whole paragraph after an edit.

    python pdf_short_lines.py main.pdf --pages 12-27 [--json]
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:  # pragma: no cover - environment-dependent error path
    sys.exit("PyMuPDF is required (import fitz).")

WORD_RE = re.compile(r"[A-Za-z0-9]+(?:[’'\-][A-Za-z0-9]+)*")


def parse_pages(spec: str | None, page_count: int) -> set[int]:
    if not spec:
        return set(range(1, page_count + 1))
    pages: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            lo_s, hi_s = part.split("-", 1)
            lo, hi = int(lo_s), int(hi_s)
            if lo > hi:
                lo, hi = hi, lo
            pages.update(range(lo, hi + 1))
        else:
            pages.add(int(part))
    bad = sorted(p for p in pages if p < 1 or p > page_count)
    if bad:
        raise ValueError(f"page(s) outside 1-{page_count}: {bad}")
    return pages


def line_record(line: dict) -> dict | None:
    spans = [s for s in line.get("spans", []) if s.get("text", "").strip()]
    if not spans:
        return None
    text = "".join(s.get("text", "") for s in spans).strip()
    words = WORD_RE.findall(text)
    if not words:
        return None
    x0 = min(float(s["bbox"][0]) for s in spans)
    y0 = min(float(s["bbox"][1]) for s in spans)
    x1 = max(float(s["bbox"][2]) for s in spans)
    y1 = max(float(s["bbox"][3]) for s in spans)
    sizes = [round(float(s.get("size", 0.0)), 2) for s in spans for _ in s.get("text", "")]
    font_size = Counter(sizes).most_common(1)[0][0] if sizes else 0.0
    return {
        "text": text,
        "words": words,
        "word_count": len(words),
        "char_count": sum(len(w) for w in words),
        "bbox": [x0, y0, x1, y1],
        "width_pt": x1 - x0,
        "font_size_pt": font_size,
    }


def dominant_body_size(doc: fitz.Document) -> float:
    weighted: Counter[float] = Counter()
    for page in doc:
        for block in page.get_text("dict").get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = span.get("text", "").strip()
                    if text:
                        weighted[round(float(span.get("size", 0.0)), 2)] += len(text)
    return weighted.most_common(1)[0][0] if weighted else 0.0


def candidates(doc: fitz.Document, pages: set[int], args: argparse.Namespace) -> list[dict]:
    body_size = dominant_body_size(doc)
    found: list[dict] = []
    for page_number in sorted(pages):
        page = doc[page_number - 1]
        for block_index, block in enumerate(page.get_text("dict").get("blocks", []), 1):
            if block.get("type") != 0:
                continue
            lines = [rec for raw in block.get("lines", []) if (rec := line_record(raw))]
            if len(lines) < args.min_lines:
                continue
            last, penult = lines[-1], lines[-2]
            if last["word_count"] > args.max_last_words:
                continue
            if body_size and abs(last["font_size_pt"] - body_size) > args.font_tolerance:
                continue
            # A robust right edge based on full preceding lines avoids using the short
            # final line itself to define the available measure.
            right_edge = max(line["bbox"][2] for line in lines[:-1])
            slack = max(0.0, right_edge - penult["bbox"][2])
            width_needed = max(0.0, last["width_pt"] - slack)
            # If the final line already fits in the measured penultimate-line slack,
            # this is probably a forced break, heading structure, or PDF block artifact,
            # not a prose-wrap candidate.
            if width_needed < args.min_width_to_recover:
                continue
            total_word_width = sum(line["width_pt"] for line in lines)
            total_words = sum(line["word_count"] for line in lines)
            total_chars = sum(line["char_count"] for line in lines)
            avg_word_width = total_word_width / max(total_words, 1)
            avg_char_width = total_word_width / max(total_chars, 1)
            est_words = max(1, math.ceil(width_needed / max(avg_word_width, 0.1)))
            est_chars = max(1, math.ceil(width_needed / max(avg_char_width, 0.1)))
            found.append({
                "id": f"p{page_number}-b{block_index}",
                "page": page_number,
                "block": block_index,
                "bbox_pt": [round(v, 2) for v in block.get("bbox", last["bbox"])],
                "body_font_size_pt": body_size,
                "line_font_size_pt": last["font_size_pt"],
                "paragraph_line_count": len(lines),
                "penultimate_line": penult["text"],
                "final_line": last["text"],
                "final_line_words": last["word_count"],
                "penultimate_slack_pt": round(slack, 2),
                "width_to_recover_pt": round(width_needed, 2),
                "estimated_min_words_to_trim": est_words,
                "estimated_min_characters_to_trim": est_chars,
                "estimate_note": "Approximate; TeX line breaking, hyphenation, macros, and citations can change the result.",
            })
    return found


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Detect actual short final paragraph lines from rendered PDF geometry."
    )
    parser.add_argument("pdf", type=Path, help="Rendered PDF to inspect")
    parser.add_argument("--pages", help="1-based pages/ranges, e.g. 12-27,31")
    parser.add_argument("--max-last-words", type=int, default=4)
    parser.add_argument("--min-lines", type=int, default=3)
    parser.add_argument("--font-tolerance", type=float, default=0.75,
                        help="Allowed difference from dominant body font in points")
    parser.add_argument("--min-width-to-recover", type=float, default=1.0,
                        help="Ignore likely forced breaks/artifacts below this point deficit")
    parser.add_argument("--limit", type=int, default=0,
                        help="Maximum candidates to print; 0 prints all")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = parser.parse_args()

    if not args.pdf.is_file():
        parser.error(f"PDF not found: {args.pdf}")
    doc = fitz.open(args.pdf)
    try:
        selected = parse_pages(args.pages, doc.page_count)
        found = candidates(doc, selected, args)
    finally:
        doc.close()

    shown = found[: args.limit] if args.limit else found
    if args.json:
        print(json.dumps({"pdf": str(args.pdf), "candidate_count": len(found), "candidates": shown}, indent=2))
    else:
        print(f"Short final-line candidates: {len(found)}")
        for item in shown:
            print(
                f"{item['id']} page {item['page']} bbox={item['bbox_pt']} | "
                f"final={item['final_line_words']} words | recover≈{item['width_to_recover_pt']:.1f} pt | "
                f"trim≈{item['estimated_min_words_to_trim']} words/{item['estimated_min_characters_to_trim']} chars"
            )
            print(f"  previous: {item['penultimate_line']}")
            print(f"  final:    {item['final_line']}")
        if args.limit and len(found) > len(shown):
            print(f"... {len(found) - len(shown)} additional candidates omitted")
        print("Estimates are planning aids; verify every target in the post-edit PDF.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
