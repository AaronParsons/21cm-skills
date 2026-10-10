---
name: latex-page-fit
description: Bring a LaTeX document (proposal, paper, abstract) within a page or word limit without losing content or breaking format rules. Use when a document or one of its sections is over its limit, or to tighten one that is close.
---

# Fitting a LaTeX document to a page limit

Content comes first, then the rules the document must meet, then length. Most
documents that run over carry repetition and wordy phrasing; remove those
before anything that carries information. `technical-prose` has the wording
rules; this skill has the procedure and the format guardrails.

## Guardrails

These hold for every edit and are checked again at the end.

- **Take the limits from the governing document,** the solicitation or the
  journal's instructions to authors, and from any later amendment or Q&A,
  which overrides it. Not from a summary, a checklist, or memory. Write the
  limits down, section by section, with where each comes from.
- **Keep every required element.** List what the governing document requires
  in each section before cutting. Don't remove, move or weaken any of them.
- **Edit without losing information.** Keep every claim, qualifier, number,
  requirement, reason and citation. Remove a repetition only after finding
  where the same information remains stated in full.
- **Ask before cutting or moving unique content.** If a passage seems
  dispensable, name it, say what would be lost and why it might go, and wait
  for the author. Moving it to an appendix or supplement counts as cutting.
- **Don't change type to gain space:** no change of font, font size, line
  spacing, tracking or `microtype` settings, and no `\resizebox` or
  `\scalebox` around text. Reviewers and screening software check these, and
  protrusion can push glyphs past the margin. Keep any exception the governing
  document allows exactly as allowed, and record it.
- **No text past the margins.** No geometry hacks, and no overfull box that
  crosses the text block; an overfull box is a failure to fix, not to accept.
- **Scale a figure by at most 10%,** and only if every label, tick and legend
  still meets the minimum font size on the printed page (`21cm-figures`,
  `scripts/pdf_min_font.py`). Don't merge or regroup the author's figures;
  suggest it in the report instead.
- **Spacing around floats, captions, headings, lists and equations** may be
  reduced a little at a time while the parts stay clearly separated. There is
  no universal compact setting; look at each page affected.
- **Fit to the limit, not under it.** Stop at 95-100% of the allowance; the
  space is there to make the case clearly.

## Steps

1. **Measure.** Build the document so the PDF matches the source, and record
   where each section starts and ends. A total page count is not enough:
   growth in one section can hide behind a float that moved in another. Write
   down each section's length against its limit and the deficit.

2. **Find short last lines in the PDF.** A paragraph whose last line holds a
   few words costs a full line; shortening it by a few words saves that line.
   Find them in the rendered PDF, not the source:

       python skills/latex-page-fit/scripts/pdf_short_lines.py main.pdf --pages 12-27 --json

   For each candidate the script gives the last two printed lines and roughly
   how much width must be recovered. Look at each one on the page and drop
   equations, captions, headings, list items and intentional breaks. Map the
   rest to source lines by searching for their words.

3. **Edit all of them as one batch,** without lossy cuts (`technical-prose`).
   Aim a little past the estimated reduction. If a paragraph can't be shortened
   that much without losing something, leave it. Don't rebuild after each
   edit: one rebuild at the end is enough, and repeated rebuild-and-tweak loops
   waste time chasing reflows.

4. **Remove repetition between parts of the document.** Where text recites
   numbers already in a table or figure, keep the interpretation in the text
   and refer to the table. Where a later section restates an earlier one,
   replace the restatement with a precise reference, unless the governing
   document requires the content in both places. Keep one complete treatment.

5. **Then layout.** Tables: span the text width, size columns by how much
   text each holds, and phrase cells in compact columns (status, margin,
   units) to fit one line so the width they free goes to the descriptive
   columns. Run-in headings (`\paragraph` or a bold lead-in) for short
   subsections, and inline lists for short items, where the structure stays
   readable. Then spacing, within the guardrails.

6. **If the deficit remains, stop and ask.** List the candidate passages for
   cutting or moving: location, length, purpose, whether it is required, and
   what would be lost. Don't edit them until the author agrees.

7. **Verify.** Rebuild fully (bibliography and cross-references included;
   another pass if the table of contents changed length). Then:
   - section lengths against the limits;
   - `pdf_short_lines.py` again on the same pages: mark each target resolved,
     still short, moved, or new;
   - `skills/latex-audit/scripts/latex_audit.py`: no new overfull boxes,
     undefined references or placeholders;
   - minimum font sizes on changed pages, including figures;
   - every required element still present, and nothing unique lost (compare
     with the version before).

## Report

End with a short log:

| Section | Before | After | Limit | What changed |
|---|---|---|---|---|

then: the short-line targets and their outcome; every figure or spacing
change; any exceptions relied on; any cuts or moves the author approved
(or "none"); and the checks in step 7 with their results. Put any suggested
figure redesigns here, not in the document.
