#!/usr/bin/env python3
"""Make a redline of a memo against its previous release.

    python <skills>/latex-memo/scripts/redline.py <memo>/memo-NNN.tex --base <ref>
        [--out <memo>/memo-NNN-redline.pdf] [--latexdiff PATH | --fetch DIR]
        [--engine pdflatex]

<ref> is the git commit (or branch, e.g. origin/main) holding the previous
release of the memo. The script

1. takes the old source from ``git show <ref>:<path>`` and the new one from the
   working tree, which must be the committed release being made; the previous
   release is named by the last commit on <ref> that touched the memo directory;
2. runs latexdiff on the two (``--type=UNDERLINE --subtype=SAFE``: additions
   underlined, deletions struck through);
3. adds a note under the title naming both commits and what the markup does not
   cover;
4. builds the result in a temporary copy of the memo directory, so that every
   figure, generated table and number macro is the new release's, running the
   TeX engine twice; and
5. writes the PDF to --out and prints the commits and the latexdiff version.

Only text in the main .tex file is marked. Figures, ``\\input`` files (generated
tables, the number macros) and new floats appear at the new version without
markup; a changed number shows as the old typed text struck out beside the new
macro value, or not at all if both were macros.

latexdiff is a Perl script. If it is not on PATH, --fetch DIR downloads the
pinned release below into DIR, checks its SHA-256 and runs its self-contained
``latexdiff-so``.
"""
import argparse
import hashlib
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

LATEXDIFF = {
    "version": "1.3.4",
    "url": "https://github.com/ftilmann/latexdiff/releases/download/1.3.4/latexdiff-1.3.4.tar.gz",
    "sha256": "aed1c39d51e5c7a8894a5e4b7190106e93968dd90edcc0dde803fcbffe01b2b4",
}


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                          check=True).stdout


def fetch(dest):
    """The pinned latexdiff release, checked against its SHA-256; returns latexdiff-so."""
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    tgz = dest / Path(LATEXDIFF["url"]).name
    if not tgz.exists():
        urllib.request.urlretrieve(LATEXDIFF["url"], tgz)
    got = hashlib.sha256(tgz.read_bytes()).hexdigest()
    if got != LATEXDIFF["sha256"]:
        raise SystemExit(f"{tgz}: SHA-256 {got} does not match the pinned {LATEXDIFF['sha256']}")
    with tarfile.open(tgz) as t:
        t.extractall(dest)
    return dest / f"latexdiff-{LATEXDIFF['version']}" / "latexdiff-so"


def note(old, new):
    """LaTeX for the note placed under the title."""
    return ("\\begin{center}\\fbox{\\parbox{0.9\\linewidth}{\\small\\textbf{Redline} of this "
            f"version (\\texttt{{{new}}}) against the previous release (\\texttt{{{old}}}). "
            "Additions are underlined and deletions struck through. Figures, generated tables "
            "and number macros are shown at this version without markup.}}\\end{center}\n")


def insert_note(tex, text):
    """Put ``text`` after \\maketitle, else straight after \\begin{document}."""
    for pat in (r"\\maketitle\b", r"\\begin\{document\}"):
        m = re.search(pat, tex)
        if m:
            return tex[:m.end()] + "\n" + text + tex[m.end():]
    raise ValueError("no \\maketitle or \\begin{document} to put the note after")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("tex", type=Path, help="the memo's main .tex file, at the new release")
    ap.add_argument("--base", required=True, help="git ref of the previous release")
    ap.add_argument("--out", type=Path, help="output PDF (default: <name>-redline.pdf beside the .tex)")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--latexdiff", help="latexdiff executable or script")
    g.add_argument("--fetch", type=Path, help="download the pinned latexdiff release into this directory")
    ap.add_argument("--engine", default="pdflatex")
    a = ap.parse_args()

    tex = a.tex.resolve()
    memo = tex.parent
    repo = Path(git(memo, "rev-parse", "--show-toplevel").strip())
    rel = tex.relative_to(repo).as_posix()
    if git(repo, "status", "--porcelain", "--untracked-files=no", "--", rel).strip():
        raise SystemExit(f"{rel} has uncommitted changes; commit the release first")
    # the previous release: the last commit on the base that touched the memo's directory
    old_rev = git(repo, "log", "-1", "--format=%h", a.base, "--", memo.relative_to(repo).as_posix()).strip()
    new_rev = git(repo, "rev-parse", "--short", "HEAD").strip()
    old = git(repo, "show", f"{a.base}:{rel}")
    tool = str(fetch(a.fetch)) if a.fetch else (a.latexdiff or shutil.which("latexdiff"))
    if not tool:
        raise SystemExit("latexdiff not found: install it, or pass --latexdiff PATH or --fetch DIR")
    cmd = (["perl", tool] if tool.endswith(("-so", ".pl")) or not shutil.which(tool) else [tool])
    out = (a.out or memo / f"{tex.stem}-redline.pdf").resolve()
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / memo.name
        shutil.copytree(memo, work, ignore=shutil.ignore_patterns(".git", "*.aux", "*.log", "*.out"))
        (work / f"{tex.stem}-previous.tex").write_text(old)
        diff = subprocess.run(cmd + ["--type=UNDERLINE", "--subtype=SAFE", f"{tex.stem}-previous.tex",
                                     tex.name], cwd=work, capture_output=True, text=True, check=True).stdout
        name = f"{tex.stem}-redline"
        (work / f"{name}.tex").write_text(insert_note(diff, note(old_rev, new_rev)))
        for _ in range(2):
            # the engine wraps its terminal output at a fixed byte count, which can split a
            # multi-byte UTF-8 character; only the "!" error lines are read from it
            r = subprocess.run([a.engine, "-interaction=nonstopmode", f"{name}.tex"], cwd=work,
                               capture_output=True, text=True, encoding="utf-8", errors="replace")
        errors = [l for l in r.stdout.splitlines() if l.startswith("!")]
        if errors or not (work / f"{name}.pdf").exists():
            raise SystemExit("redline did not build:\n" + "\n".join(errors[:10]))
        shutil.copy(work / f"{name}.pdf", out)
    v = subprocess.run(cmd + ["--version"], capture_output=True, text=True)
    version = (v.stdout + v.stderr).strip().splitlines()
    print(f"wrote {out}\n  previous release {old_rev} ({a.base}), this release {new_rev}\n"
          f"  {version[0] if version else 'latexdiff'}")


if __name__ == "__main__":
    sys.exit(main())
