# 21cm-skills

Rules and tools for 21-cm and radio data analysis, figures, spectral analysis
and technical writing, packaged as [Agent Skills](https://agentskills.io): one
directory per skill, holding a `SKILL.md` (frontmatter `name` and
`description`, then the rules) and optional `scripts/`. Claude Code, Codex and
Antigravity all read this format, and each loads a skill only when its
description matches the task.

| Skill | Use it to | Requires |
|---|---|---|
| `21cm-analysis` | reduce data and make claims: weighted means, radiometer noise, model comparison, simulations, validation, scope | |
| `spectral-analysis` | compute delay, fringe-rate and other transforms of flagged data: windows and sidelobes, edge ringing, flag-gap leakage, scattering by a varying mask, broadcast flags; `flag_cover.py` covers a flag mask with a few shapes so a few DPSS filters serve every slice | |
| `21cm-figures` | make figures: axes, scales, colour maps, model-comparison panels, waterfalls, printed text size, captions | |
| `technical-prose` | write and revise document text: direct, said once, quantitative; signs of padding and unvetted generated text | `latex-audit` |
| `latex-audit` | review a LaTeX memo, paper or proposal and report its problems without editing | `21cm-figures` |
| `latex-page-fit` | bring a LaTeX document within a page limit without losing content or breaking format rules | `latex-audit`, `21cm-figures` |
| `latex-memo` | write, change and rebuild a living memo: one products script, numbers as macros, provenance, branch → build → checks → merge | `latex-audit`, `21cm-figures` |

"Requires" are skills whose scripts a skill runs; every install method below
brings them along. `skills.json` has the full index.

## Install

### Into a project, for any agent: `install.py`

Copies chosen skills into a project, where Claude Code reads `.claude/skills`
and Codex and Antigravity read `.agents/skills`. The source commit is recorded
in `.21cm-skills.json` in each directory, so a project is reproducible and its
skills travel with its repository.

```bash
curl -fsSL https://raw.githubusercontent.com/AaronParsons/21cm-skills/main/install.py \
    | python3 - 21cm-analysis spectral-analysis

# or, from a clone
python3 install.py --list
python3 install.py --project ~/src/myproj --agents claude,codex latex-memo
python3 install.py --user --all          # ~/.claude/skills, ~/.agents/skills, ~/.gemini/...
python3 install.py --status              # what is installed, from which commit, edited?
python3 install.py --update              # refresh copies (skips any you have edited)
python3 install.py --remove latex-page-fit
```

| agent | `--project DIR` | `--user` |
|---|---|---|
| Claude Code | `DIR/.claude/skills` | `~/.claude/skills` |
| Codex | `DIR/.agents/skills` | `~/.agents/skills` |
| Antigravity (`agy`) | `DIR/.agents/skills` | `~/.gemini/config/skills`, `~/.gemini/antigravity-cli/skills` |

If `.claude/skills` and `.agents/skills` link to the same directory, skills are
installed there once. The installer never overwrites a skill directory it did
not install, or a copy edited since it was installed, unless given `--force`.
`--link` symlinks to a local clone instead of copying, which is the mode for
developing the skills.

### As a Claude Code plugin

```text
/plugin marketplace add AaronParsons/21cm-skills
/plugin install all@21cm-skills              # every skill
/plugin install latex-memo@21cm-skills       # one skill and what it requires
```

Plugin skills are namespaced (`latex-memo:latex-memo`) and installed per user,
so they follow you across projects on a machine. To give a project's
collaborators the marketplace automatically, add it to `.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "21cm-skills": {"source": {"source": "github", "repo": "AaronParsons/21cm-skills"}}
  },
  "enabledPlugins": {"all@21cm-skills": true}
}
```

Plugins carry no version, so `/plugin marketplace update 21cm-skills` brings in
the latest commit.

### As a Codex plugin

```bash
codex plugin marketplace add AaronParsons/21cm-skills
```

Then install `all` or a single skill from the plugin directory. The Codex
marketplace is `.agents/plugins/marketplace.json`, and each plugin has a
`.codex-plugin/plugin.json`.

## Layout

```text
skills/<name>/SKILL.md, scripts/     the skills: the only hand-edited source
skills.json                          index: description, requires, related   (generated)
plugins/<name>/                      one plugin per skill plus its requirements;
plugins/all/                         every skill                             (generated)
.claude-plugin/marketplace.json      Claude Code marketplace                 (generated)
.agents/plugins/marketplace.json     Codex marketplace                       (generated)
install.py                           the cross-agent installer
tools/build.py                       regenerates everything marked generated
tests/                               installer and build tests
```

Plugin directories hold symlinks into `skills/`; Claude Code copies their
targets when it installs a plugin.

## Changing a skill

1. Edit `skills/<name>/SKILL.md` (or its scripts). Write each rule as an
   imperative with its reason, and keep skills free of any one project's
   specifics; those belong in the project's own `AGENTS.md` or `CLAUDE.md`.
2. Refer to a script by its path under the skills directory,
   `<skills>/<name>/scripts/<file>`. A reference to another skill's script
   makes that skill a requirement.
3. Run `python3 tools/build.py`, then `python3 -m pytest`.
4. Add a dated line to `CHANGELOG.md`.

CI fails if the generated files are out of date or a test fails.

## Licence

MIT; see `LICENSE`.
