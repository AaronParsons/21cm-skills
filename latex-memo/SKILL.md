---
name: latex-memo
description: Build and edit the living LaTeX memos in memos/. Covers how to run tectonic from the `tex` micromamba env, the make_figures.py → numbers.tex → memo.tex workflow, and figure rules. Figures should show fundamental observables in their measurement domain, and compare data to model with residuals in three panels or three stacked line plots on shared axes. Use when creating, updating, compiling, or adding figures to any memo.
---

# LaTeX memos

## Building

LaTeX comes from **tectonic**, installed in its own micromamba env, `tex`. Python
(numpy, matplotlib, newnucal, hera_sim, …) lives in the `arp` env. In
non-interactive shells, neither `python` nor `tectonic` is on `PATH`, so call the
env binaries explicitly:

```bash
PY=~/micromamba/envs/arp/bin/python
TEX="$HOME/.local/bin/micromamba run -n tex tectonic"   # or ~/micromamba/envs/tex/bin/tectonic

cd memos/<memo_name>
$PY make_figures.py                 # all figures + numbers.tex (can take minutes)
$PY make_figures.py <fig> [<fig>…]  # re-run only some figures; merges into numbers.json
$TEX -X compile memo.tex            # writes memo.pdf
```

In an interactive shell you can also activate the env:
`eval "$(micromamba shell hook --shell bash)" && micromamba activate tex`.

- The first compile downloads TeX packages into tectonic's cache, so it needs network
  access. Later compiles are offline-fast.
- Check the build:
  `$TEX -X compile memo.tex 2>&1 | grep -iE "error|overfull|undefined"` should
  print nothing. Fix overfull boxes: long `\texttt{paths}` become `\nolinkurl{...}`,
  and long inline equations become display math.
- Look at the result before calling it done. Rasterize with
  `pdftoppm -png -r 70 memo.pdf <scratchpad>/page` and Read the pages, and do the
  same for each figure PDF.
- Run long figure scripts with `run_in_background`, then wait on the completion
  notification.
- Before circulating a memo, compile with `--keep-logs` and run the mechanical audit,
  `$PY ../../skills/latex-audit/scripts/latex_audit.py memo.tex --log memo.log`. It should
  report no serious findings. For a full review, follow `latex-audit`.

Claims in a memo follow `21cm-analysis`, figures follow `21cm-figures` as well as the
rules below, and the text follows `technical-prose`.

## Memo conventions

Each memo is a directory `memos/<name>/` containing:

- `memo.tex`: begins with a **Status + Changelog** box. Bump the version and add a
  dated changelog line for every substantive update. These are living documents,
  so record what changed and what was learned. Don't silently overwrite.
- `make_figures.py`: the single source of every figure and every quoted number.
  Inputs that are not yet known go in one clearly marked block (e.g. `OBS = dict(...)`)
  tagged `PLACEHOLDER`.
- `numbers.tex` / `numbers.json`: auto-generated `\newcommand` macros. **Never
  type a computed number into the prose.** Quote it through a macro, so a
  re-run keeps text and figures consistent. Macro names must be letters only;
  use `A,B,C…` suffixes rather than digits.
- `figures/*.pdf`: vector figures, written by the script only.

Additional rules:

- Mark placeholder values in orange with a `\placeholder{}` macro, and list
  them in an inputs table with their source and status.
- Keep a caveats/approximations section and a next-steps/open-questions section.
- Prefer `\begin{thebibliography}` over BibTeX. Don't invent journal
  volume or page numbers you haven't verified; author + year + short title is fine.

## Figure rules

### 1. Plot fundamental observables, in the domain where they are measured

Choose axes the instrument actually measures, or that are one linear transform away:

- visibilities vs. frequency, time/LST, or baseline;
- delay spectra |Ṽ(τ)|, and fringe-rate × delay;
- power spectra P(k∥, k⊥) or cylindrical/delay power;
- uv-plane or image-plane maps in physical units (λ, m, ns, mHz, Jy, K);
- gains, beams and kernels vs. frequency or angle.

**Avoid abstracted statistics** when a direct comparison in the measurement
domain would show the same thing more effectively. Examples: "fraction of cells
above a threshold", a summary score vs. a parameter, a χ² curve, or a histogram
of residual ratios. If a reader would trust the conclusion more by *seeing* data
and model overlaid, show that instead.

A summary statistic is appropriate only when:
- the point really is a scan over many configurations that can't be shown directly; or
- it accompanies, rather than replaces, at least one direct measurement-domain comparison of a
  representative case.

Even then:
- state what the statistic is, and why it stands in for the observable, in the caption;
- keep its axes in physical units where possible, e.g. "suppression of delay power at τ > 500 ns" rather than a dimensionless score.

### 2. Compare data to model with residuals, on shared axes

Whenever a figure compares a measurement (or truth) to a model or fit, show
**data, model, and residual together**:

- **2-D quantities** (uv maps, delay × fringe-rate, waterfalls, power spectra) get a
  **three-panel row**: data | model | residual.
  - All three use the **same axes and extent** (`sharex=True, sharey=True`).
  - Data and model share **one color scale and one colorbar**.
  - The residual gets a diverging map centered on zero (two hues + neutral midpoint) and
    its own colorbar. Alternatively, put it on the same scale as data and model when the
    point is how small it is.
  - Label the residual's definition, e.g. `data − model` or `(data − model)/σ`.
- **1-D quantities** (spectra, delay profiles, time series) get **three stacked
  panels sharing the x-axis**: data, model, residual.
  - Use the same y-scale for data and model (`sharey` for the top two).
  - Draw a zero line on the residual panel.
  - The stacked layout can be replaced by data and model overlaid in the top panel, with
    the residual below, when the overlay reads clearly.
- Keep the residual's **noise level visible**: a ±1σ band or a σ-normalized axis.
  "Small" is meaningless without the noise reference.
- Use the same layout and scales across a figure series, so before/after or
  config-to-config comparisons are visual, not numeric.

```python
fig, ax = plt.subplots(1, 3, figsize=(7.0, 2.6), sharex=True, sharey=True,
                       constrained_layout=True)
norm = LogNorm(vmin, vmax)                       # shared by data and model
for a, img, t in zip(ax[:2], (data, model), ("data", "model")):
    im = a.imshow(img.T, origin="lower", extent=ext, norm=norm, cmap=SEQ)
    a.set_title(t)
fig.colorbar(im, ax=ax[:2], shrink=0.8)
lim = np.nanmax(np.abs(resid))
imr = ax[2].imshow(resid.T, origin="lower", extent=ext, cmap=DIVERGING,
                   vmin=-lim, vmax=lim)
ax[2].set_title("data − model")
fig.colorbar(imr, ax=ax[2], shrink=0.8)

fig, ax = plt.subplots(3, 1, figsize=(3.5, 4.2), sharex=True,
                       constrained_layout=True)  # 1-D version
ax[0].plot(x, data); ax[1].plot(x, model); ax[1].sharey(ax[0])
ax[2].plot(x, data - model); ax[2].axhline(0, lw=0.6, color=MUTED)
ax[2].fill_between(x, -sigma, sigma, color=NEUTRAL, lw=0)
```

### 3. Style

Follow the `dataviz` skill:
- one-hue sequential maps for magnitude, and diverging maps for signed residuals;
- categorical colors assigned in fixed order;
- thin lines, recessive grids and spines;
- direct labels or a legend, never color alone;
- no dual y-axes.

For print memos, use a white surface and `pdf.fonttype=42`. Set sizes so text is
about 7–8 pt at 7.0 in width.
