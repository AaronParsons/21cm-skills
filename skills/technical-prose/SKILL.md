---
name: technical-prose
description: Rules for writing and revising technical prose (memos, papers, proposals, READMEs, captions) so it is direct, quantitative and checkable, and for spotting padding and unvetted generated text. Read before drafting or revising any document text, and when tightening text to fit a limit.
---

# Technical prose

Each rule is an imperative with its reason. They apply to text written by a
person or an agent, and to editing either. Shortening text must keep every
claim, qualifier, number and citation; `latex-page-fit` has the procedure
for fitting a limit.

(`<skills>` is the directory this skill is installed in: its parent, e.g. `.claude/skills`, `.agents/skills` or a plugin's `skills/`.)

## Say it directly

- **State the claim, not that you are about to.** Cut throat-clearing: "It is
  important to note that X" is "X"; "It can be seen from Figure 4 that X" is
  "X (Fig. 4)"; "in order to" is "to"; "due to the fact that" is "because".
- **Use verbs, not nouns made from them.** "performs a measurement of" is
  "measures"; "provides a demonstration of" is "demonstrates"; "carries out the
  calibration of" is "calibrates".
- **Name who or what acts.** "The pipeline flags the data" says who does it in
  fewer words than "The data are flagged by the pipeline".
- **Fold an equation's introduction into the claim it supports:** "The
  antenna temperature combines sky and receiver terms (Eq. 3):", not a
  sentence announcing that an equation follows.
- **Cite parenthetically** unless the authors are the point of the sentence:
  "...probes the first stars (Pritchard & Loeb 2012)", not "As shown in the
  comprehensive study by Pritchard and Loeb (2012), ...".

## Say it once

- **Text interprets; tables and figures hold the inventory.** Don't recite in
  prose the numbers a table already lists. Say what they mean (which margin
  is tight, what drives it) and point to the table.
- **Give each topic one complete treatment** and refer to it from elsewhere,
  with a precise reference (section, table, equation). Don't make the reader
  assemble an argument from fragments, and don't restate background in each
  section.
- **Recaps and summaries say something new** (a consequence, a comparison) or
  go.

## Say it quantitatively

- **Replace an adjective of quality with the number behind it.** Not "robust
  margins" but "a 3.2× margin on the 1 mK allocation"; not "dramatically
  reduces" but "reduces the variance six-fold".
- **Quote numbers to the precision their uncertainty supports,** with units,
  and from the script or macro that computes them, never typed in.
- **Match the strength of the words to the evidence.** "Consistent with" until
  a test has ruled out the alternatives (`21cm-analysis`); "shows" only for
  what the figure or number shows.
- **Define every acronym and symbol at first use,** and use one name for one
  thing throughout.

## Signs of padding or unvetted generated text

When revising, reread any sentence that has one of these. They don't prove
anything; they mark where the text may say less than it seems to.
`<skills>/latex-audit/scripts/latex_audit.py --style` lists most of the phrases.

- **Promotional verbs and adjectives:** delve, seamless, a testament to,
  shatters, revolutionises, groundbreaking, unprecedented, pivotal, cutting-edge,
  state-of-the-art, plays a key role. Replace with what happens and by how much.
- **Empty intensifiers:** fundamentally, crucially, truly, real (as in "the
  real problem"), robust (without a number).
- **The "not X, but Y" frame,** used for emphasis where nobody claimed X.
- **One template stamped on every item:** each objective, subsystem or data
  product given the same sentence shape and the same suspiciously perfect
  numbers ("100% recall, 0% false positives"). Each item gets the numbers its
  own analysis produced.
- **Numbers outside their physical range or at false precision:** a
  reflectivity above 1, an angle above 180°, a margin of thousands from
  dividing by a slope near zero, a pointing error to 0.001° from a 1′ sensor.
- **Text carried over from elsewhere:** another project's name or dimensions,
  rules from a different call for proposals, a cross-reference to the wrong
  appendix, a placeholder (TBD, TBC) left in.
- **Citations that don't support their sentence,** or that name a different
  author from the one the text names (`latex-audit` step 3).
