import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("redline", Path(__file__).with_name("redline.py"))
redline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(redline)


def test_note_goes_after_maketitle():
    tex = "\\begin{document}\n\\maketitle\nBody\n\\end{document}\n"
    out = redline.insert_note(tex, "NOTE\n")
    assert out.index("NOTE") > out.index("\\maketitle") and out.index("NOTE") < out.index("Body")


def test_note_without_title_goes_after_begin_document():
    out = redline.insert_note("\\begin{document}\nBody\n\\end{document}", "NOTE\n")
    assert out.index("NOTE") < out.index("Body")


def test_note_needs_a_document():
    with pytest.raises(ValueError):
        redline.insert_note("no document here", "NOTE\n")


def test_note_names_both_commits():
    n = redline.note("abc1234", "def5678")
    assert "abc1234" in n and "def5678" in n
