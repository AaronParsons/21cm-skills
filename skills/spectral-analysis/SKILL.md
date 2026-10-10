---
name: spectral-analysis
description: Rules and tools for delay, fringe-rate and other Fourier or DPSS transforms of gridded, flagged data, covering windowing, sidelobes, edge ringing, leakage from flag gaps, power scattered by a sample-varying mask, and broadcasting flags. Includes flag_cover.py, which covers a flag mask with a few shapes so a few DPSS filters serve every slice. Read before computing or interpreting a delay spectrum, fringe-rate spectrum, delay × fringe-rate map, or any filter or projection along a data axis.
---

# Spectral analysis of flagged data

These rules go with `21cm-analysis` (noise, weights, validation) and
`21cm-figures` (how to plot the result). Each rule is an imperative with its
reason.

(`<skills>` is the directory this skill is installed in: its parent, e.g. `.claude/skills`, `.agents/skills` or a plugin's `skills/`.)

The common failure is the same in every form: the transform of the window,
the mask or the filter is convolved with the bright part of the data and
spreads it to where faint signals are sought. With a bright core 10⁵–10⁶
times the noise, a leak of 10⁻⁵ is a detection.

## Windows and sidelobes

- **Taper every axis you transform.** A rectangular window's sidelobes fall
  only as 1/k², so the core of a bright signal leaks across the whole
  spectrum. Use a window whose sidelobe level is below the dynamic range you
  need. Blackman–Harris (4-term) has sidelobes near −92 dB, about 10⁻⁹ in
  power; Hann sits near −31 dB and is not enough for a 10⁶ core.
- **Know what the window costs.** A taper widens the main lobe (Blackman–Harris
  is about 2× wider than Hann) and lowers the effective number of samples.
  Leave a buffer of a few resolution elements between a region you measure and
  the edge of the core you exclude.
- **Normalise noise through the same window.** The noise power in a windowed
  transform is Σ W² σ², not N σ². Write power in units of that, so that 1
  means noise in every cell.
- **Don't filter by zeroing FFT bins and transforming back.** A hard mask in
  the transform domain rings across the whole block (Gibbs), worst at its
  edges; a quantity that is largest at the block edges is this artifact.
  Remove a band with a fit to a basis that spans it, such as DPSS vectors, or
  taper the mask.

## Flag gaps

- **A flagged sample is a hole in the window.** Multiplying a taper by the
  flag mask convolves the spectrum with the mask's transform. A single missing
  sample in a block of N spreads roughly (1/N)² of the core's power, flat,
  across the whole conjugate axis; a few missing samples or channels can set a
  floor far above the window's own sidelobes.
- **Inpainted or down-weighted samples are holes too.** Giving them zero
  weight in a windowed FFT is the same as flagging them. If the data are
  inpainted, decide which you want: the inpainted values (no hole, but a model
  in the data) or zero weight (a hole). Say which in the caption.
- **Estimate the leakage floor from the mask itself.** Transform the window ×
  mask, normalise to its peak, and compare its sidelobe level with the
  dynamic range you need. Better still, pass a noiseless model through the same
  window and mask: whatever appears outside its true support is leakage.

## Weighted fits and scattering by a varying mask

- **Prefer weighted least-squares fits to a band-limited basis (DPSS) over
  FFTs when the data have gaps.** A fit handles missing samples without
  ringing. It is not free of leakage: power outside the basis's band
  projects onto the fitted coefficients, by an amount that depends on the mask.
  Regularise the fit (an eigenvalue cutoff on the basis, or a small ridge).
- **A mask that changes along one axis scatters power along the other.** If
  the flags (or weights) differ from one time sample to the next, a per-sample
  fit in frequency has a different bias each sample. That bias is proportional
  to the signal, so it modulates the bright core in time and spreads it across
  all fringe rates, looking like real, sky-correlated structure. The same holds
  with the axes swapped.
- **Test for it by freezing the mask.** Before interpreting faint structure on
  the conjugate axis, repeat the measurement with a mask and weights that are
  constant along the axis you fit (see broadcasting, below). If the structure
  survives, it is in the data; if it vanishes, it was the mask.

## Broadcasting flags

- **Broadcast flags along an axis to make the mask separable.** Flag a channel
  at every time if it is flagged at any time (or a time at every channel, or
  across all baselines of a group). Then every slice along the other axis
  shares one mask.
- **Then build one filter and reuse it.** With a shared mask, the DPSS design
  matrix, its weighted Gram matrix and the inverse are the same for every
  slice. Compute them once and apply them to all slices. Every slice gets the
  same filter response, so nothing varies from slice to slice to scatter
  power, and the cost drops from one solve per slice to one.
- **Use weights that don't vary along the axis either, if the test needs it.**
  Per-sample weights (e.g. from varying sample counts) also change the fit from
  slice to slice. Replace them with their mean along the axis for the test.
- **Count what broadcasting costs.** Report the fraction of data dropped. It is
  usually small when bad samples cluster in a few channels or times. When it
  is large, cover the flags with a few masks (see Tools) rather than keep a
  sample-varying mask. Hundreds of distinct masks often reduce to fewer than
  ten at under 1% extra flagging.

## Tools: covering flags with a few shapes

`scripts/flag_cover.py` (numpy and scipy only) finds masks that contain every
flagged cell, so that a few filters serve every slice. Flags are boolean, with
the filter axis last (e.g. frequency for a delay filter); every other index is
a slice (time, baseline, ...).

```python
import sys; sys.path.insert(0, "<skills>/spectral-analysis/scripts")
from flag_cover import separable_cover, pattern_cover, FilterBank

rows, cols = separable_cover(flags2d)          # whole rows + whole columns
cover = pattern_cover(flags, max_patterns=8, drop_frac=0.5)
print(cover.summary())                         # masks, slices dropped, extra flagged
bank = FilterBank(A, cover)                    # A: (nf, nmodes) DPSS basis
model = bank.fit(data)                         # one projector per mask, reused
resid = bank.residual(data)                    # NaN wherever the cover flags
```

- **Try the separable cover first.** It flags whole rows and columns, so one
  filter serves each axis and 2-D fits stay separable. It is a minimum-weight
  bipartite vertex cover, solved exactly by min-cut, for the additive cost
  (row costs plus column costs). That counts a cell where a chosen row meets a
  chosen column twice, so it overstates the loss when many rows and columns
  are chosen.
- **If it costs too much, use a few masks.** `pattern_cover` gives each slice
  one of K masks that contains its own flags. The cover is a union of K outer
  products: the slices assigned to mask k × mask k. It merges masks greedily,
  always joining the pair that adds the fewest flagged cells. Stop at
  `max_patterns` or at a budget `max_extra_frac`. Drop slices that are mostly
  flagged (`drop_frac`) rather than give them their own masks.
- **Report the cost.** `summary()` gives the masks, the dropped slices and the
  extra flagged fraction. Quote the fraction with any result that uses the
  cover.
- **Build each filter once.** `FilterBank` computes one weighted DPSS projector
  per mask. Every slice sharing a mask gets the identical filter, and the cost
  is K solves instead of one per slice. Weights must be the same for all
  slices that share a mask.
- Tests: `python -m pytest <skills>/spectral-analysis/scripts/test_flag_cover.py`.

## Checking a faint feature

Before claiming structure at levels near the leakage floor:

1. Measure it two ways, a windowed FFT and a weighted DPSS fit with no FFT.
   Window sidelobes and edge ringing affect only the first.
2. Repeat it with a broadcast (time-invariant) mask and weights. Scattering by
   a varying mask affects both methods and disappears with this.
3. Pass a model with no such feature through the identical window, mask and
   filter. What it shows is the method's own floor.
4. Say in the text and caption which window, mask treatment and filter were
   used.
