"""Keep matplotlib figure text at its intended size once LaTeX scales the figure.

matplotlib font sizes are points at the figure's native ``figsize``. When the
saved figure is placed narrower than it was drawn (``\\includegraphics[width=...]``),
every piece of text shrinks by the same ratio: an 11-inch figure placed at
6.4 in prints its 8 pt legend at 4.6 pt. Draw the figure at its printed width
where you can. Where you can't, call ``rescale_fonts_for_print`` just before
``savefig`` so each text artist prints at the size it was set to.

Get the printed width from the document, not by guessing: put
``\\showthe\\textwidth`` (or ``\\the\\linewidth`` inside the float) in the
source, read the value in points from the log, and divide by 72.27.

Usage, from a script outside this directory::

    sys.path.insert(0, "<skills>/21cm-figures/scripts")
    from print_fonts import rescale_fonts_for_print
    ...
    rescale_fonts_for_print(fig, display_width_in=0.9 * TEXTWIDTH_IN, min_print_pt=8)
    fig.savefig(path, bbox_inches="tight")
"""
import matplotlib
import matplotlib.text


def rescale_fonts_for_print(fig, display_width_in, native_width_in=None, min_print_pt=None):
    """Scale every text artist in ``fig`` so it prints at its set size.

    ``display_width_in`` is the width, in inches, at which the saved figure
    is placed on the page. ``min_print_pt``, if given, raises any text set
    smaller than it to that size on the printed page (a solicitation's or
    journal's minimum). Call after all layout is final. Returns the scale
    factor applied (saved width / printed width).

    ``bbox_inches="tight"`` re-crops the canvas around whatever was drawn,
    including the enlarged text this function sets, so the saved figure can
    end up wider than ``native_width_in`` and print smaller than intended.
    The scale is therefore iterated against the measured tight bounding box
    (plus ``savefig.pad_inches``) until it stops changing. Pass
    ``native_width_in`` only if you save without ``bbox_inches="tight"``;
    it then fixes the scale and no iteration is done.
    """
    fig.canvas.draw()  # materialize tick labels and offset text first
    texts, sizes = [], []
    for txt in fig.findobj(matplotlib.text.Text):
        sz = txt.get_fontsize()
        if sz:
            texts.append(txt)
            sizes.append(float(sz) if min_print_pt is None else max(float(sz), float(min_print_pt)))

    def apply(scale):
        for txt, sz in zip(texts, sizes):
            txt.set_fontsize(sz * scale)
        fig.canvas.draw()

    if native_width_in is not None:
        scale = native_width_in / display_width_in
        apply(scale)
        return scale

    pad_in = matplotlib.rcParams["savefig.pad_inches"]
    if not isinstance(pad_in, (int, float)):  # "layout" in newer matplotlib
        pad_in = 0.0
    scale = fig.get_size_inches()[0] / display_width_in
    # The iteration contracts; how many passes it needs grows with how much
    # the text inflates the bounding box. Each pass is one redraw.
    for _ in range(20):
        apply(scale)
        renderer = fig.canvas.get_renderer()
        new_scale = (fig.get_tightbbox(renderer).width + 2 * pad_in) / display_width_in
        if abs(new_scale - scale) < 1e-4:
            break
        scale = new_scale
    apply(scale)
    return scale
