"""Tests for install.py and tools/build.py.  Run: python3 -m pytest"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
INSTALL = [sys.executable, str(ROOT / "install.py")]
INDEX = json.loads((ROOT / "skills.json").read_text())


def run(args, cwd, env=None, ok=True):
    r = subprocess.run(INSTALL + args, cwd=cwd, capture_output=True, text=True,
                       env={**os.environ, **(env or {})})
    if ok:
        assert r.returncode == 0, r.stderr
    return r


def test_generated_files_are_current():
    r = subprocess.run([sys.executable, str(ROOT / "tools/build.py"), "--check"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout


def test_index_matches_skills():
    names = {p.parent.name for p in (ROOT / "skills").glob("*/SKILL.md")}
    assert set(INDEX) == names
    for n, v in INDEX.items():
        assert v["description"]
        for req in v["requires"]:
            assert req in names
            assert f"<skills>/{req}/" in (ROOT / "skills" / n / "SKILL.md").read_text()


def test_plugins_hold_their_requirements():
    for n, v in INDEX.items():
        have = {p.name for p in (ROOT / "plugins" / n / "skills").iterdir()}
        need = {n, *v["requires"]}
        todo = list(need)
        while todo:                                  # transitive requirements
            for r in INDEX[todo.pop()]["requires"]:
                if r not in need:
                    need.add(r)
                    todo.append(r)
        assert have == need
        for p in (ROOT / "plugins" / n / "skills").iterdir():
            assert (p / "SKILL.md").is_file()        # symlink resolves
    assert {p.name for p in (ROOT / "plugins/all/skills").iterdir()} == set(INDEX)


def test_marketplaces_list_every_plugin():
    claude = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text())
    codex = json.loads((ROOT / ".agents/plugins/marketplace.json").read_text())
    want = set(INDEX) | {"all"}
    assert {p["name"] for p in claude["plugins"]} == want
    assert {p["name"] for p in codex["plugins"]} == want
    for p in claude["plugins"]:
        assert (ROOT / p["source"] / ".claude-plugin/plugin.json").is_file()
    for p in codex["plugins"]:
        assert (ROOT / p["source"]["path"] / ".codex-plugin/plugin.json").is_file()


def test_no_project_specifics_in_skill_paths():
    for p in (ROOT / "skills").glob("*/SKILL.md"):
        text = p.read_text()
        assert "](skills/" not in text and " skills/" not in text.replace("<skills>/", ""), p


def test_install_project_all_agents_with_requirements(tmp_path):
    run(["latex-memo"], tmp_path)
    for d in (".claude/skills", ".agents/skills"):
        got = {p.name for p in (tmp_path / d).iterdir() if p.is_dir()}
        assert got == {"latex-memo", *INDEX["latex-memo"]["requires"]}
        lock = json.loads((tmp_path / d / ".21cm-skills.json").read_text())
        assert set(lock) == got and all(v["mode"] == "copy" and v["hash"] for v in lock.values())


def test_install_one_agent_and_remove(tmp_path):
    run(["--agents", "claude", "21cm-analysis"], tmp_path)
    assert (tmp_path / ".claude/skills/21cm-analysis/SKILL.md").is_file()
    assert not (tmp_path / ".agents").exists()
    run(["--agents", "claude", "--remove", "21cm-analysis"], tmp_path)
    assert not (tmp_path / ".claude/skills/21cm-analysis").exists()


def test_shared_directory_installed_once(tmp_path):
    (tmp_path / "skills").mkdir()
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".agents").mkdir()
    (tmp_path / ".claude/skills").symlink_to("../skills")
    (tmp_path / ".agents/skills").symlink_to("../skills")
    r = run(["spectral-analysis"], tmp_path)
    assert r.stdout.count("copied spectral-analysis") == 1
    assert (tmp_path / "skills/spectral-analysis/scripts/flag_cover.py").is_file()


def test_foreign_and_edited_skills_are_protected(tmp_path):
    d = tmp_path / ".claude/skills/21cm-analysis"
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text("mine")
    r = run(["--agents", "claude", "21cm-analysis"], tmp_path)
    assert "skip" in r.stdout and (d / "SKILL.md").read_text() == "mine"
    run(["--agents", "claude", "--force", "21cm-analysis"], tmp_path)
    assert (d / "SKILL.md").read_text() != "mine"
    with open(d / "SKILL.md", "a") as f:
        f.write("\n- a local rule\n")
    r = run(["--agents", "claude", "--update"], tmp_path)
    assert "edited since it was installed" in r.stdout
    assert (d / "SKILL.md").read_text().endswith("- a local rule\n")
    assert "EDITED" in run(["--agents", "claude", "--status"], tmp_path).stdout


def test_link_mode(tmp_path):
    run(["--agents", "codex", "--link", "technical-prose"], tmp_path)
    p = tmp_path / ".agents/skills/technical-prose"
    assert p.is_symlink() and p.resolve() == (ROOT / "skills/technical-prose").resolve()


def test_user_scope_paths(tmp_path):
    run(["--user", "--agents", "agy", "21cm-figures"], tmp_path, env={"HOME": str(tmp_path)})
    for d in (".gemini/config/skills", ".gemini/antigravity-cli/skills"):
        assert (tmp_path / d / "21cm-figures/SKILL.md").is_file()


def test_unknown_skill_fails(tmp_path):
    r = run(["no-such-skill"], tmp_path, ok=False)
    assert r.returncode != 0 and "unknown skill" in (r.stderr + r.stdout)
