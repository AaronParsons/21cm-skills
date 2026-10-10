#!/usr/bin/env python3
"""Install chosen skills into a project (or your user directories) for Claude
Code, Codex and Antigravity.

    python3 install.py --list
    python3 install.py 21cm-analysis spectral-analysis          # into ./ for all agents
    python3 install.py --project ~/src/foo --agents claude latex-memo
    python3 install.py --user --all                             # every project on this machine
    python3 install.py --update                                 # refresh what is installed here
    python3 install.py --status                                 # what is installed; edited copies
    python3 install.py --remove latex-page-fit

Without a clone, fetch and run it directly:

    curl -fsSL https://raw.githubusercontent.com/AaronParsons/21cm-skills/main/install.py \\
        | python3 - 21cm-analysis

Where skills go:

    agent        --project DIR                --user
    claude       DIR/.claude/skills           ~/.claude/skills
    codex        DIR/.agents/skills           ~/.agents/skills
    agy          DIR/.agents/skills           ~/.gemini/config/skills and
                                              ~/.gemini/antigravity-cli/skills

Skills a chosen skill requires (it runs their scripts) are installed with it.
Copies are the default and record the source commit in
<dest>/.21cm-skills.json; --link symlinks to a local clone instead, so edits in
the clone take effect at once (for developing the skills, not for sharing a
project).  Directories that are symlinks to each other (e.g. .claude/skills ->
../skills) are installed once.  A skill directory that this tool did not
install, or a copy edited since it was installed, is never overwritten unless
--force is given.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_URL = "https://github.com/AaronParsons/21cm-skills.git"
CACHE = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "21cm-skills"
LOCK = ".21cm-skills.json"
AGENTS = ("claude", "codex", "agy")


def source_repo(ref, offline):
    """A checkout holding skills/: this script's own clone, or a cached clone."""
    f = globals().get("__file__")
    here = Path(f).resolve().parent if f and Path(f).is_file() else None
    if here and (here / "skills").is_dir() and (here / "skills.json").is_file():
        return here
    if not (CACHE / ".git").is_dir():
        if offline:
            sys.exit(f"--offline but no cached clone at {CACHE}")
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "--quiet", REPO_URL, str(CACHE)], check=True)
    if not offline:
        subprocess.run(["git", "-C", str(CACHE), "fetch", "--quiet", "--tags", "origin"], check=True)
        target = ref if ref and ref.startswith("v") else f"origin/{ref or 'main'}"
        subprocess.run(["git", "-C", str(CACHE), "checkout", "--quiet", "--detach", target],
                       check=True)
    return CACHE


def commit_of(repo):
    r = subprocess.run(["git", "-C", str(repo), "describe", "--always", "--dirty"],
                       capture_output=True, text=True)
    return r.stdout.strip() or "unknown"


def destinations(args):
    if args.user:
        home = Path.home()
        table = {"claude": [home / ".claude/skills"], "codex": [home / ".agents/skills"],
                 "agy": [home / ".gemini/config/skills", home / ".gemini/antigravity-cli/skills"]}
    else:
        p = Path(args.project).expanduser().resolve()
        table = {"claude": [p / ".claude/skills"], "codex": [p / ".agents/skills"],
                 "agy": [p / ".agents/skills"]}
    out, seen = [], set()
    for a in args.agents:
        for d in table[a]:
            key = os.path.realpath(d)
            if key not in seen:
                seen.add(key)
                out.append(d)
    return out


def closure(index, names):
    out, todo = [], list(names)
    while todo:
        n = todo.pop(0)
        if n not in index:
            sys.exit(f"unknown skill {n!r}; see --list")
        if n not in out:
            out.append(n)
            todo += index[n]["requires"]
    return out


def tree_hash(d):
    """SHA-256 over a skill directory's files (paths and contents), ignoring caches."""
    h = hashlib.sha256()
    for f in sorted(p for p in Path(d).rglob("*") if p.is_file()
                    and "__pycache__" not in p.parts and p.suffix != ".pyc"):
        h.update(str(f.relative_to(d)).encode() + b"\0" + f.read_bytes() + b"\0")
    return h.hexdigest()


def read_lock(d):
    f = d / LOCK
    return json.loads(f.read_text()) if f.is_file() else {}


def write_lock(d, lock):
    if lock:
        (d / LOCK).write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n")
    elif (d / LOCK).exists():
        (d / LOCK).unlink()


def remove_path(p):
    if p.is_symlink() or p.is_file():
        p.unlink()
    elif p.exists():
        shutil.rmtree(p)


def install(repo, names, dests, link, force):
    commit = commit_of(repo)
    for d in dests:
        d.mkdir(parents=True, exist_ok=True)
        lock = read_lock(d)
        for n in names:
            src, dst = repo / "skills" / n, d / n
            if (dst.exists() or dst.is_symlink()) and not force:
                if n not in lock:
                    print(f"  skip {dst}: exists and was not installed by this tool (use --force)")
                    continue
                if lock[n].get("mode") == "copy" and lock[n].get("hash") \
                        and tree_hash(dst) != lock[n]["hash"]:
                    print(f"  skip {dst}: edited since it was installed; move the edits to the "
                          f"21cm-skills repo, or use --force to discard them")
                    continue
            remove_path(dst)
            if link:
                dst.symlink_to(src)
            else:
                shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            lock[n] = {"commit": commit, "mode": "link" if link else "copy",
                       "source": REPO_URL if repo == CACHE else str(repo)}
            if not link:
                lock[n]["hash"] = tree_hash(dst)
            print(f"  {'linked' if link else 'copied'} {n} -> {dst}")
        write_lock(d, lock)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("skills", nargs="*", help="skills to install (their requirements come too)")
    where = ap.add_mutually_exclusive_group()
    where.add_argument("--project", default=".", help="project directory (default: .)")
    where.add_argument("--user", action="store_true", help="install for every project")
    ap.add_argument("--agents", default=",".join(AGENTS),
                    help=f"comma-separated subset of {','.join(AGENTS)} (default: all)")
    ap.add_argument("--all", action="store_true", help="install every skill")
    ap.add_argument("--list", action="store_true", help="list skills and exit")
    ap.add_argument("--update", action="store_true", help="reinstall every skill installed here")
    ap.add_argument("--status", action="store_true",
                    help="show installed skills, their commits, and any edited since install")
    ap.add_argument("--remove", action="store_true", help="remove the named skills")
    ap.add_argument("--link", action="store_true", help="symlink to a local clone instead of copying")
    ap.add_argument("--force", action="store_true", help="overwrite skills this tool did not install")
    ap.add_argument("--ref", default=None, help="branch or tag to install from (default: main)")
    ap.add_argument("--offline", action="store_true", help="use the cached clone as it is")
    args = ap.parse_args()
    args.agents = [a.strip() for a in args.agents.split(",") if a.strip()]
    bad = [a for a in args.agents if a not in AGENTS]
    if bad:
        sys.exit(f"unknown agents {bad}; choose from {AGENTS}")

    repo = source_repo(args.ref, args.offline)
    index = json.loads((repo / "skills.json").read_text())
    if args.list:
        for n, v in index.items():
            req = f"  [requires: {', '.join(v['requires'])}]" if v["requires"] else ""
            print(f"{n}{req}\n    {v['description']}\n")
        return
    dests = destinations(args)
    if args.status:
        for d in dests:
            lock = read_lock(d)
            print(f"{d}: {len(lock)} skills from this tool")
            for n, v in sorted(lock.items()):
                edited = (v.get("mode") == "copy" and (d / n).is_dir()
                          and tree_hash(d / n) != v.get("hash"))
                print(f"  {n:20s} {v['mode']:5s} {v['commit']}" + ("  EDITED" if edited else ""))
        return
    if args.remove:
        for d in dests:
            lock = read_lock(d)
            for n in args.skills:
                if n in lock:
                    remove_path(d / n)
                    del lock[n]
                    print(f"  removed {d / n}")
            write_lock(d, lock)
        return
    if args.update:
        for d in dests:
            lock = read_lock(d)
            if lock:
                links = [n for n, v in lock.items() if v.get("mode") == "link"]
                copies = [n for n in lock if n not in links]
                if copies:
                    install(repo, closure(index, copies), [d], False, False)
                print(f"  {d}: {len(copies)} copied skills refreshed"
                      + (f"; {len(links)} linked skills follow their clone" if links else ""))
        return
    names = list(index) if args.all else args.skills
    if not names:
        ap.error("name skills to install, or use --all, --list or --update")
    names = closure(index, names)
    if args.link and repo == CACHE:
        print("note: --link points into the shared cache clone; prefer a clone of your own")
    print(f"installing {', '.join(names)} from {commit_of(repo)}")
    install(repo, names, dests, args.link, args.force)


if __name__ == "__main__":
    main()
