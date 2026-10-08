---
name: latex-audit
description: Review a LaTeX document (memo, paper, proposal) for what a reader, referee or reviewer would trip on, and report the problems without editing. Use when asked to review, audit or check a document before it is circulated, submitted or merged.
---

# Auditing a LaTeX document

An audit finds problems; it doesn't fix them. Don't edit the document during
one. Report only what is wrong, at risk, or needs someone outside the session
to confirm. Don't list what passes, and don't list strengths.

## Steps

1. **Build it, then audit the built document.** Audit what the reader gets: a
   file in the repo that the document never includes is not content, however
   authoritative it looks. Rebuild if the log is older than the sources.

2. **Run the mechanical checks:**

       python skills/latex-audit/scripts/latex_audit.py main.tex \
           [--generated <dir of generated .tex/.csv>] [--cite-context] [--style]

   It follows the `\input` tree from the main file and reports placeholders,
   citation keys missing from the `.bib`, `.bib` entries missing author, title
   or year, duplicate labels, references to undefined labels, overfull boxes
   (major >= 15 pt, moderate 5-15 pt, minor < 5 pt, with the source file),
   undefined references and citations from the log, and, with `--generated`,
   generated files nothing in the document uses.

3. **Read the citations against what they cite** (`--cite-context` prints
   each citing sentence beside the cited title and first author). Flag a
   citation whose work doesn't support its sentence, and a sentence that names
   an author ("as Smith et al. showed") whose citation has a different first
   author. Mismatched citations are the commonest sign of unchecked generated
   text.

4. **Check numbers for consistency across the document.** The same quantity
   (a mass, a rate, a margin, a sample size) must agree wherever it appears:
   abstract, text, tables, figures, captions, appendices. A number typed into
   the text instead of coming from the macro or script that computes it is a
   finding in itself. So are:
   - a precision the uncertainty doesn't support;
   - a margin or allowance outside the physical range (a reflectivity above 1,
     an angle above 180°, a "10,000×" margin from dividing by a near-zero
     slope).

5. **Check figures at printed size:**
   - `skills/21cm-figures/scripts/pdf_min_font.py` on the built PDF for the
     smallest text;
   - the rest of the `21cm-figures` checks by eye on the page.

6. **Check the requirements the document answers to.** For a proposal or
   journal submission, list the governing document's requirements (page and
   section limits, required sections and tables, fonts, margins, file size)
   from the document itself and its latest amendment or Q&A, which overrides
   it. Never from a cached checklist or summary: requirement numbers and limits
   in those drift. Audit each requirement and record the ones that fail. For a
   memo, the requirements are `latex-memo` and `AGENTS.md` § Memos.

7. **Read for prose** with `technical-prose` (`--style` lists phrases to
   reread). Look for text carried over from another document: another
   project's name, a different instrument's numbers, rules from the wrong
   solicitation.

## Report

Order findings by severity: disqualifying or wrong first, then at risk, then
cosmetic. For each, give:

- **status:** `[FAIL]`, `[AT RISK]` (incomplete, a placeholder, or relying on
  an assumption nobody has confirmed), or `[EXTERNAL]` (needs someone outside
  the session to confirm, e.g. a signature or an institutional number);
- **where:** file and line, page, table cell, or requirement number;
- **evidence:** the text or number that shows it;
- **next step:** what would fix it.

End with a short prioritised list of fixes.
