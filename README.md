# skills

Agent procedures and portable rules for this workspace, one directory per skill with a
`SKILL.md` (frontmatter `name` and `description`, then the steps).
`../.claude/skills` and `../.agents/skills` are symlinks here, so Claude Code
and Antigravity load them; other agents read the files directly. `AGENTS.md`
§ Skills has the rule for keeping them current. A skill's helper scripts sit
in its `scripts/` directory; run them from the repo root by path, or put that
directory on `sys.path` to import them.

| Skill | Use it to |
|---|---|
| `21cm-analysis` | reduce data and make claims: weighted means, radiometer noise, model comparison, simulations, validation, scope (portable) |
| `21cm-figures` | make figures: axes, scales, colour maps, model-comparison panels, waterfalls, printed text size, captions (portable) |
| `technical-prose` | write and revise document text: direct, said once, quantitative; signs of padding and unvetted generated text (portable) |
| `latex-audit` | review a LaTeX memo, paper or proposal and report its problems without editing (portable) |
| `latex-page-fit` | bring a LaTeX document within a page limit without losing content or breaking format rules (portable) |
| `latex-memo` | write, change and rebuild a living memo: one products script, numbers as macros, provenance, branch → build → checks → merge (portable; project settings in `AGENTS.md` § Memos) |

## Recent changes

- 2026-10-08: installed in specred. `.claude/skills` and `.agents/skills`
  link here. `memo-rebuild` was EIGSEP-specific (paths, campaign variables,
  `make_products.py`, pdflatex), so its steps are now the portable `latex-memo`
  (which absorbed specred's memo build and figure rules), and project settings
  go in `AGENTS.md` § Memos. `latex-memo` adds: memo numbering, a provenance
  record that includes separately versioned packages, and a check for running
  jobs before moving a memo directory. `latex-audit` now points to
  `latex-memo`.

- 2026-10-07: rules and tools carried over from the BLOOM-21cm SMEX proposal.
  New `technical-prose`, `latex-audit` (with `latex_audit.py`) and
  `latex-page-fit` (with `pdf_short_lines.py`). `21cm-analysis`: median flags
  past 50% occupancy, simulation results tied to their configuration, derived
  rather than typed numbers, linearised margins, crediting fixes.
  `21cm-figures`: printed text size, with `print_fonts.py`, `textfit.py` and
  `pdf_min_font.py`. `memo-rebuild` runs `latex_audit.py` in step 6. Added the
  `.agents/skills` symlink.

- 2026-10-07: rules from the memo 008 work. `21cm-analysis`: index by coordinate,
  name direction frames, check results with and without a mask, name degenerate
  columns, equal-freedom alternatives, one-variable controls. `21cm-figures`:
  compare models in observing coordinates with data, show a test's decision
  region and counts, show measurements against raw data, check the rendered page.
  `memo-rebuild`: branch-only products and a merge fallback.

- 2026-10-07: added `21cm-analysis` and `21cm-figures`, portable to other
  21-cm projects: Aaron's plotting notes plus the general rules that were in
  `AGENTS.md` § Analysis methodology, which now points to them and keeps only
  the EIGSEP lessons.
- 2026-10-07: added `memo-rebuild`, the steps memos 003-006 each repeated
  (clean-tree regeneration, numbers diff, PDF text check, merge on Aaron's OK).
