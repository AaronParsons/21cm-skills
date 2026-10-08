---
name: memo-rebuild
description: Change an EIGSEP memo (memos/memo-NNN-*/) and regenerate its figures, tables, quoted numbers and PDF with clean provenance. Use whenever a memo's text, its make_products.py, or an input it reads changes.
---

# Rebuilding an EIGSEP memo

Memos follow `AGENTS.md` § Memos. Each `memos/memo-NNN-<topic>/` holds
`memo-NNN.tex`, a `make_products.py` that writes `figures/`, `tables/`
(including `tables/numbers.tex`, the LaTeX macros for every quoted number) and
a provenance table, and the committed `memo-NNN.pdf`. Some memos also have slow
`validate_*.py` scripts whose outputs (`.npz`/`.json`) sit beside them and are
read by `make_products.py`.

## Steps

1. **Work in a worktree on a branch**, never in the shared checkout:
   `git -C /mnt/data02/eigsep fetch -q && git -C /mnt/data02/eigsep worktree add -b <branch> <scratchpad>/wt-<name> origin/main`.
   Point the campaign at the real data: `export EIGSEP_CAMPAIGN_ROOT=/mnt/data02/eigsep/marjum-2026-07`.
   Use the arp env: `/home/aparsons/.local/share/mamba/envs/arp/bin/python3`.
   If the memo needs package code from another worktree or branch, put
   `PYTHONPATH=<that worktree>/src` first (the editable install is `main`).
   If the memo reads new data products that exist only on this branch, write
   them into the worktree's `marjum-2026-07/` with the generator's `--out-dir`,
   never the shared checkout (untracked copies there block switching it to
   `main` once they merge). Then point `EIGSEP_CAMPAIGN_ROOT` at the worktree's
   `marjum-2026-07/` and copy in any gitignored inputs the memo reads. Set
   `EIGSEP_RAW_ROOT=/mnt/data02/eigsep/marjum-2026-07` for raw correlator files,
   where the memo's script supports it.

2. **Edit the source.** Figures follow `skills/21cm-figures`, and claims follow
   `skills/21cm-analysis`. Put every number the text quotes into
   `make_products.py` as a macro and use `\macroName` in the `.tex`; never type
   a measured number into the text. Inputs come from tracked products, the
   campaign's gitignored products (checksummed by the script), or a validation
   output in the memo directory. Never read from or cite `scratch/` or a
   session scratchpad. When the result is refined or overturned, rewrite the
   affected sections in place and update `\date{... This version: YYYY-MM-DD}`.
   Add a revision-history line only for a significant change in understanding.
   Update the memo's `README.md` (file table if files changed; one dated line at
   the top of `## Recent changes`).

3. **Run any validation script that changed** (they are slow; run in the
   background and wait on the PID). Its output file lives in the memo directory
   and is committed.

4. **Commit the source first**, with explicit pathspecs and no AI trailers:
   `git commit -m "memo NNN: <what changed>" -- <paths>`. The provenance stamp
   is `-dirty` if anything tracked is modified when `make_products.py` starts,
   including generated outputs from an earlier run, so `git status --short`
   must show nothing tracked before step 5. Discard stale outputs with
   `git checkout -- <memo>/figures <memo>/tables <memo>/memo-NNN.pdf` if needed.

5. **Regenerate and build:**
   `python make_products.py && pdflatex -interaction=nonstopmode memo-NNN.tex >/dev/null && pdflatex -interaction=nonstopmode memo-NNN.tex | grep -E "^!|undefined"`
   (twice, for references). Only `h float specifier changed` warnings are
   expected.

6. **Check before committing products:**
   - `git diff tables/numbers.tex`: only the numbers you meant to change moved.
     An unexpected change means an input or package changed under you; find out
     why before going on.
   - `grep commit tables/provenance.tex`: no `-dirty`.
   - Read the changed passage in the PDF (there is no `pdftotext` here):
     `python3 -c "import fitz; print(''.join(p.get_text() for p in fitz.open('memo-NNN.pdf')))" | grep -A8 "<phrase>"`.
     Macros that render oddly (e.g. `0.00%`) need a format change in
     `make_products.py`, then go back to step 4.
   - LaTeX table rows written from Python end in `+ r"\\"`; a single
     backslash breaks the build.
   - `python ../../skills/latex-audit/scripts/latex_audit.py memo-NNN.tex`: no
     placeholders, undefined references or major overfull boxes. For a fuller
     review before circulating the memo, follow `latex-audit`.

7. **Commit the products** (`figures/`, `tables/`, the PDF) as
   `memo NNN: regenerate products at <source commit>`, push the branch to the
   hub (`origin`), and report what changed with the key numbers.

8. **Merge only on Aaron's direct OK in the session.** Then from the shared
   checkout: `git fetch -q && git merge --ff-only <branch> && git push -q origin main`,
   remove the worktree, and delete the branch locally and on the hub. If that
   cannot fast-forward (`main` moved, or the shared checkout is on another
   branch or has someone else's unpushed commits):
   - merge `origin/main` into the branch in the worktree;
   - rebuild and check the memo there (steps 5-6);
   - push `<branch>:main` from the worktree;
   - fast-forward the shared checkout only if it is on `main`, clean, and has no
     local commits; otherwise leave it and say so.
