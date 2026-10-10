#!/usr/bin/env python3
"""Generate the skill index, plugins and marketplaces from skills/.

    python tools/build.py           # write skills.json, plugins/, both marketplaces
    python tools/build.py --check   # exit 1 if anything is out of date (CI)

skills/<name>/SKILL.md is the only source.  Everything else is generated:

  skills.json                          name, description, requires, related
  plugins/<name>/                      one plugin per skill: the skill plus the
                                       skills it requires (symlinks into skills/)
  plugins/all/                         every skill
  .claude-plugin/marketplace.json      Claude Code marketplace
  .agents/plugins/marketplace.json     Codex marketplace
  plugins/*/.claude-plugin/plugin.json, plugins/*/.codex-plugin/plugin.json

"requires" are the skills whose scripts a skill runs (`<skills>/<other>/...`
in its SKILL.md); installing a skill installs them too.  "related" are other
skills it names in backticks, which it reads but does not need.

No plugin sets a version, so installs follow the repository's commits.
"""
import json
import os
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
PLUGINS = ROOT / "plugins"
MARKET = "21cm-skills"
OWNER = {"name": "Aaron Parsons", "email": "aparsons@berkeley.edu",
         "url": "https://github.com/AaronParsons"}
REPO = "https://github.com/AaronParsons/21cm-skills"
ALL = "all"


def frontmatter(path):
    text = path.read_text()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        raise ValueError(f"{path}: no YAML frontmatter")
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith(" "):
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    for k in ("name", "description"):
        if not meta.get(k):
            raise ValueError(f"{path}: frontmatter lacks {k!r}")
    if meta["name"] != path.parent.name:
        raise ValueError(f"{path}: name {meta['name']!r} differs from its directory")
    return meta, text


def index():
    skills = {}
    texts = {}
    for p in sorted(SKILLS.glob("*/SKILL.md")):
        meta, text = frontmatter(p)
        skills[meta["name"]] = {"description": meta["description"]}
        texts[meta["name"]] = text
    names = set(skills)
    for n, text in texts.items():
        req = sorted(set(re.findall(r"<skills>/([a-z0-9-]+)/", text)) - {n})
        missing = [r for r in req if r not in names]
        if missing:
            raise ValueError(f"{n}: requires unknown skills {missing}")
        rel = sorted({m for m in re.findall(r"`([a-z0-9-]+)`", text) if m in names} - {n} - set(req))
        skills[n]["requires"] = req
        skills[n]["related"] = rel
    return skills


def closure(skills, names):
    out, todo = set(), list(names)
    while todo:
        n = todo.pop()
        if n not in out:
            out.add(n)
            todo += skills[n]["requires"]
    return sorted(out)


def plugin_files(skills):
    """{relative path: content or ('link', target)} for every generated file."""
    files = {}
    groups = {n: closure(skills, [n]) for n in skills}
    groups[ALL] = sorted(skills)
    for g, members in groups.items():
        desc = (skills[g]["description"] if g in skills
                else f"All {len(members)} skills: " + ", ".join(members) + ".")
        manifest = {"name": g, "description": desc, "author": OWNER, "homepage": REPO,
                    "repository": REPO, "license": "MIT"}
        files[f"plugins/{g}/.claude-plugin/plugin.json"] = json.dumps(manifest, indent=2) + "\n"
        files[f"plugins/{g}/.codex-plugin/plugin.json"] = json.dumps(manifest, indent=2) + "\n"
        for m in members:
            files[f"plugins/{g}/skills/{m}"] = ("link", f"../../../skills/{m}")
    names = sorted(groups, key=lambda g: (g != ALL, g))
    files[".claude-plugin/marketplace.json"] = json.dumps({
        "name": MARKET,
        "owner": OWNER,
        "description": "Rules and tools for 21-cm and radio data analysis, figures, spectral "
                       "analysis and technical writing, as Agent Skills.",
        "plugins": [{"name": g, "source": f"./plugins/{g}",
                     "description": (skills[g]["description"] if g in skills
                                     else "Every skill in this marketplace.")}
                    for g in names],
    }, indent=2) + "\n"
    files[".agents/plugins/marketplace.json"] = json.dumps({
        "name": MARKET,
        "interface": {"displayName": "21cm skills"},
        "plugins": [{"name": g, "source": {"source": "local", "path": f"./plugins/{g}"},
                     "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
                     "category": "Productivity"} for g in names],
    }, indent=2) + "\n"
    files["skills.json"] = json.dumps(skills, indent=2) + "\n"
    return files


def current(rel):
    p = ROOT / rel
    if p.is_symlink():
        return ("link", os.readlink(p))
    if p.is_file():
        return p.read_text()
    return None


def main():
    check = "--check" in sys.argv
    files = plugin_files(index())
    stale = [rel for rel, want in files.items() if current(rel) != want]
    expected_plugins = {rel.split("/")[1] for rel in files if rel.startswith("plugins/")}
    extra = sorted(p.name for p in PLUGINS.iterdir() if p.name not in expected_plugins) \
        if PLUGINS.exists() else []
    extra_links = []
    for g in expected_plugins:
        d = PLUGINS / g / "skills"
        if d.exists():
            extra_links += [str(x.relative_to(ROOT)) for x in d.iterdir()
                            if str(x.relative_to(ROOT)) not in files]
    if check:
        if stale or extra or extra_links:
            print("out of date:", *stale, *[f"plugins/{e}" for e in extra], *extra_links,
                  sep="\n  ")
            print("run: python tools/build.py")
            sys.exit(1)
        print("generated files are up to date")
        return
    for e in extra:
        shutil.rmtree(PLUGINS / e)
    for x in extra_links:
        (ROOT / x).unlink()
    for rel in stale:
        p = ROOT / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        want = files[rel]
        if p.is_symlink() or p.exists():
            p.unlink() if (p.is_symlink() or p.is_file()) else shutil.rmtree(p)
        if isinstance(want, tuple):
            p.symlink_to(want[1])
        else:
            p.write_text(want)
    print(f"wrote {len(stale)} files; {len(extra)} stale plugins removed")


if __name__ == "__main__":
    main()
