---
name: 21cm-figures
description: Conventions for figures of radio and 21-cm cosmology data (axes, scales, colour maps, model comparisons, waterfalls, captions). Read before making or revising any plot or figure, in a memo, notebook, PR or conversation.
---

# Figures of 21-cm data

These rules go with `21cm-analysis`, whose rules on averaging and noise apply
to every plotted quantity.

(`<skills>` is the directory this skill is installed in: its parent, e.g. `.claude/skills`, `.agents/skills` or a plugin's `skills/`.)

## Axes and scales

- **Plot in fundamental coordinates:** time, frequency, fringe rate, delay,
  baseline, and (u, v). Plot signal in Jy, K, uncalibrated correlator power, or
  SNR. Label every axis with its unit, and say which noise an SNR divides by. A
  derived metric needs a reason, and its definition goes in the caption.
- **Show dynamic range with logarithmic axes and colour scales.** Signed
  quantities get a symmetric linear range where possible. Otherwise use symlog,
  with the linear threshold near the radiometer noise level, or log |x| with
  the two signs in different symbols or colours.
- **Give panels the reader compares the same axis limits and colour scale.**
  Choose the limits deliberately, not per panel by default.
- **Waterfalls:** time runs down the page from top to bottom, and frequency or
  delay increases to the right. Label the time axis with its reference (UTC or
  LST). Use a logarithmic colour scale unless the quantity is signed.

## Colour and marks

- **Use colour maps by role:** perceptually uniform sequential maps (e.g.
  viridis) for magnitudes, diverging maps centred on zero for signed residuals,
  and cyclic maps for phase. Never use jet. Choose colour-blind-safe pairs for
  lines and symbols.
- **Show flagged samples as blank (NaN),** never as zeros or interpolated
  values, and name the flag version in the caption.
- **Show complex data as amplitude and phase (or real and imaginary).** Don't
  show amplitude alone when the phase carries the information.
- **Leave out annotations that don't carry information.** Every colour, symbol
  and label should mean something.

## Model comparisons

- **Models mapped into observing coordinates are compared with data in those
  coordinates.** A model in its own frame (a simulated beam on the sphere, a sky
  map) can stand alone. Once it is mapped into what the instrument records (time,
  frequency, pointing), show it against the data it predicts, or leave it out.
- **Show the data as measured, the model in the same coordinates, and the
  residual (data minus model).**
  - For 1-D plots, put data and model on the same axes where possible, with the
    residual in a panel below that shares the x axis.
  - For images and scatter plots, use three panels with shared x and y. Data and
    model get identical colour scales, often logarithmic. The residual gets a
    linear scale symmetric about zero.
  - Where possible, plot the residual in units of radiometer σ, or draw the
    predicted noise level on it, so the reader can see whether the model is
    good enough.

## Tests and measurements

- **A figure of a test shows the test:** the thresholds or decision region,
  marked on the plot, and the counts on each side for the test and its null.
- **Show a derived measurement against the rawest data that carries it,** with
  the instrument's state marked along the shared axis (switch state, pointing,
  interference sources), so the reader can see where it comes from.

## Samples and statistics

- **Show illustrative samples along an axis, or every sample if there are few
  enough, rather than summary statistics.** At these dynamic ranges, a summary
  hides what matters. When you do summarise, use weighted means, and show the
  spread or the worst case with it.

## Checking the rendered figure

Look at the figure as it will be read (the PDF page, the notebook cell), not
the code:

- legends and labels clear of the data;
- the figure and its caption fit on the page;
- every derived quantity on an axis (e.g. "power / its 2-h median") defined on
  the axis or in the caption.

## Captions

Every figure has a caption, including figures shown in a conversation, notebook
or PR. A caption:

1. states directly what is plotted and where the data came from (the data
   product and its version, the window, and the selection);
2. says why the figure matters to the question or diagnosis at hand;
3. points the reader to the features that carry that information.

## Size and text on the printed page

- **Draw a figure at the width it is printed at.** matplotlib font sizes are
  points at the figure's own `figsize`; placing an 11-inch figure 6.4 inches
  wide prints its 8 pt legend at 4.6 pt. Read the printed width from the
  document (`\showthe\textwidth`, or `\the\linewidth` inside the float, in
  points; divide by 72.27). Where the figure must be drawn wider, call
  `scripts/print_fonts.py`'s `rescale_fonts_for_print(fig, display_width_in)`
  just before `savefig`. It also takes a minimum printed size.
- **Size boxes for text by measuring the text.** A generated table, summary
  graphic or chart that counts characters to fit text overflows; measure
  strings as matplotlib sets them with `scripts/textfit.py`. If text doesn't
  fit at the minimum size, change the box or the text, not the font.
- **Check the smallest text in the built document,** not in the figure file:
  `python <skills>/21cm-figures/scripts/pdf_min_font.py <doc>.pdf --below <pt>`.
  Where a minimum applies (a journal's or a solicitation's), every figure
  meets it at printed size. Text in raster images needs checking by eye.

## Reproducibility

Every figure kept beyond a conversation is regenerated by a script from named,
versioned data products. Don't edit figures by hand.
