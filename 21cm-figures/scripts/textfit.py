"""Measure and wrap text as matplotlib will set it, in points.

Character counts lie: a column that fits 16 characters of one string fits 12
of another whose letters are wider. A generated table, summary graphic or
chart that sizes its boxes by counting characters overflows them. Everything
here measures a string as matplotlib draws it, so a box sized to hold n lines
does hold them.

Mathtext spans ($...$) are atomic: they are never broken across lines, since
half of a math span does not render. An escaped \\$ is a literal dollar sign.

    from textfit import text_pt, wrap, fits, largest_size
    lines = wrap(label, avail=72 * 1.4, size=8)          # 1.4 in wide
    size = largest_size(label, avail=72 * 1.4, max_lines=2, sizes=[10, 9, 8])
"""
import re

_fig = None
_cache = {}
_MATH = re.compile(r"(?<!\\)\$(?:[^$\\]|\\.)*(?<!\\)\$")


def _figure():
    global _fig
    if _fig is None:
        import matplotlib
        import matplotlib.figure
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        _fig = matplotlib.figure.Figure(figsize=(1, 1), dpi=100)
        FigureCanvasAgg(_fig)
        _fig.canvas.draw()
    return _fig


def text_pt(s, size, bold=False, italic=False, family=None):
    """Width of ``s`` in points at ``size`` points, as matplotlib sets it.

    ``family`` defaults to matplotlib's current ``font.family``; pass the
    family the figure actually uses.
    """
    key = (s, size, bold, italic, family)
    if key in _cache:
        return _cache[key]
    fig = _figure()
    kw = {"family": family} if family else {}
    t = fig.text(0, 0, s, fontsize=size,
                 fontweight="bold" if bold else "normal",
                 style="italic" if italic else "normal", **kw)
    width = t.get_window_extent(renderer=fig.canvas.get_renderer()).width * 72.0 / fig.dpi
    t.remove()
    _cache[key] = width
    return width


def _push_words(atoms, chunk):
    words = chunk.split()
    if not words:
        return
    glued = bool(atoms) and not chunk[:1].isspace()
    for i, word in enumerate(words):
        atoms.append((word, glued if i == 0 else False))


def tokens(para):
    """Split into wrappable tokens, keeping each $...$ span whole.

    A math span glues to whatever it touches without a space, so
    'SNR$_{comb}$' is one token and never strands its subscript.
    """
    atoms, pos = [], 0
    for m in _MATH.finditer(para):
        chunk = para[pos:m.start()]
        _push_words(atoms, chunk)
        glued = bool(atoms) and (not chunk[-1:].isspace() if chunk else True)
        atoms.append((m.group(0), glued))
        pos = m.end()
    _push_words(atoms, para[pos:])
    out = []
    for text, glued in atoms:
        if glued and out:
            out[-1] += text
        else:
            out.append(text)
    return out


def _break_token(token, avail, size, bold, italic, family):
    """Split one over-wide token by characters; math spans stay whole."""
    if token.lstrip().startswith("$"):
        return [token]
    out, cur = [], ""
    for ch in token:
        if cur and text_pt(cur + ch, size, bold, italic, family) > avail:
            out.append(cur)
            cur = ch
        else:
            cur += ch
    return out + [cur] if cur else [""]


def wrap(text, avail, size, bold=False, italic=False, family=None, indent=""):
    """Greedy-wrap ``text`` to ``avail`` points; return the list of lines.

    Newlines in ``text`` are hard breaks. ``indent`` is prepended to each
    continuation line (hanging bullets).
    """
    lines = []
    for para in text.split("\n"):
        cur = ""
        for token in tokens(para):
            trial = token if not cur else cur + " " + token
            if text_pt(trial, size, bold, italic, family) <= avail:
                cur = trial
                continue
            if cur:
                lines.append(cur)
                token = indent + token
            frags = _break_token(token, avail, size, bold, italic, family)
            lines.extend(frags[:-1])
            cur = frags[-1]
        lines.append(cur)
    return lines


def fits(text, avail, size, max_lines, **kw):
    """True if ``text`` wraps into at most ``max_lines`` lines at ``avail`` points."""
    return len(wrap(text, avail, size, **kw)) <= max_lines


def largest_size(text, avail, max_lines, sizes, **kw):
    """The largest of ``sizes`` at which ``text`` fits, or None if none do.

    Pass only sizes at or above the minimum you must meet; a None result
    means the box or the text has to change, not the font.
    """
    for size in sorted(sizes, reverse=True):
        if fits(text, avail, size, max_lines, **kw):
            return size
    return None
