#!/usr/bin/env python3
"""Mechanical checks on a LaTeX document: what a reader or reviewer would trip on.

    python latex_audit.py path/to/main.tex [--log main.log] [--generated DIR ...]
                          [--cite-context] [--style]

Follows \\input / \\include / \\subfile from the main file, so it checks only
what the document actually includes, and reports:

- placeholders (TBD, TBC, TODO, FIXME, XXX, ??) outside comments;
- citation keys missing from the .bib files the document names, and .bib
  entries missing author/editor, title or year, or duplicated;
- labels defined twice, and \\ref/\\eqref/\\cref targets never defined;
- from the log: overfull boxes by severity (major >= 15 pt, moderate 5-15 pt,
  minor < 5 pt, with the source file they occur in), undefined references
  and citations, and multiply defined labels;
- with --generated DIR: files in DIR that nothing the document includes
  refers to (generated but never used; don't audit those as content);
- with --cite-context: every citation's sentence beside the cited title,
  for reading by eye (no automatic topic matching);
- with --style: phrases from the technical-prose skill's list.

Prints findings only; exits 1 if any placeholder, missing key, undefined
reference or major overfull box was found.
"""
import argparse
import os
import re
import sys
from collections import Counter, defaultdict

INCLUDE = re.compile(r"\\(?:input|include|subfile)\s*\{([^}]+)\}")
CITE = re.compile(r"\\(?:[cC]ite[a-zA-Z]*|[pP]arencite|[tT]extcite|autocite|nocite)\*?(?:\[[^\]]*\]){0,2}\{([^}]+)\}")
LABEL = re.compile(r"\\label(?:\[[^\]]*\])?\{([^}]+)\}")
REF = re.compile(r"\\(?:ref|eqref|pageref|autoref|[cC]ref|[cC]pageref|nameref)\*?\{([^}]+)\}")
BIBS = re.compile(r"\\(?:bibliography|addbibresource)\s*(?:\[[^\]]*\])?\{([^}]+)\}")
PLACEHOLDER = re.compile(r"\bTBD\b|\bTBC\b|\bTODO\b|\bFIXME\b|\bXXX\b|\?\?|\\tbd\b")
OVERFULL = re.compile(r"Overfull \\([hv])box \(([0-9.]+)pt too (?:wide|high)\)(?: in (?:paragraph|alignment) at lines (\d+)--(\d+)| detected at line (\d+))?")

# Phrases that signal padding or unvetted generated prose. Each is a prompt to
# reread the sentence, not proof of anything. Keep in step with
# skills/technical-prose/SKILL.md.
STYLE = [
    r"\bdelve", r"\bseamless(?:ly)?\b", r"\btestament to\b", r"\bshatter", r"\brevolutioni[sz]",
    r"\bgroundbreaking\b", r"\bcutting-edge\b", r"\bunprecedented\b", r"\bparadigm\b",
    r"\bpivotal\b", r"\brobust(?:ly)?\b", r"\bfundamentally\b", r"\bcrucial(?:ly)?\b",
    r"\bit is (?:important|worth) (?:to note|noting|emphasi[sz]ing) that\b",
    r"\bin order to\b", r"\bdue to the fact that\b", r"\bnot (?:just|only|merely) [^.]{1,40}, but\b",
    r"\bplays? a (?:key|critical|crucial|vital) role\b", r"\bstate-of-the-art\b",
    r"\b100% (?:recall|detection)\b",
]


def strip_comments(text):
    return "\n".join(re.sub(r"(?<!\\)%.*", "", line) for line in text.splitlines())


def resolve(name, base_dirs, ext=".tex"):
    name = name.strip()
    cands = [name] if name.endswith(ext) else [name + ext, name]
    for d in base_dirs:
        for c in cands:
            p = os.path.normpath(os.path.join(d, c))
            if os.path.isfile(p):
                return p
    return None


def active_files(main):
    root = os.path.dirname(os.path.abspath(main))
    order, seen, stack = [], set(), [os.path.abspath(main)]
    missing = []
    while stack:
        f = stack.pop()
        if f in seen:
            continue
        seen.add(f)
        order.append(f)
        with open(f, encoding="utf-8", errors="ignore") as fh:
            text = strip_comments(fh.read())
        for name in INCLUDE.findall(text):
            p = resolve(name, [root, os.path.dirname(f)])
            if p:
                stack.append(p)
            else:
                missing.append((f, name))
    return order, missing, root


def read_lines(files):
    """Yield (file, line number, comment-stripped line)."""
    for f in files:
        with open(f, encoding="utf-8", errors="ignore") as fh:
            for i, line in enumerate(fh, 1):
                yield f, i, re.sub(r"(?<!\\)%.*", "", line.rstrip("\n"))


def field_value(body, name):
    """The value of BibTeX field ``name`` in an entry body, braces balanced."""
    m = re.search(rf"(?i)(?:^|[,\s]){name}\s*=\s*", body)
    if not m:
        return None
    i = m.end()
    if i >= len(body):
        return None
    if body[i] == "{":
        depth = 0
        for j in range(i, len(body)):
            depth += {"{": 1, "}": -1}.get(body[j], 0)
            if depth == 0:
                return body[i + 1:j]
        return None
    if body[i] == '"':
        j = body.find('"', i + 1)
        return body[i + 1:j] if j != -1 else None
    w = re.match(r"[\w-]+", body[i:])
    return w.group(0) if w else None


def parse_bib(paths):
    entries, dups, problems = {}, [], []
    for path in paths:
        with open(path, encoding="utf-8", errors="ignore") as fh:
            text = fh.read()
        parts = re.split(r"(?m)^\s*@(\w+)\s*[{(]", text)
        for etype, body in zip(parts[1::2], parts[2::2]):
            if etype.lower() in ("string", "preamble", "comment"):
                continue
            m = re.match(r"\s*([^,\s]+)\s*,", body)
            if not m:
                continue
            key = m.group(1)
            if key in entries:
                dups.append((key, path))
            fields = {}
            for name in ("author", "editor", "title", "year", "date"):
                value = field_value(body, name)
                if value:
                    fields[name] = " ".join(re.sub(r"[{}]", "", value).split())
            entries[key] = {"path": path, **fields}
            missing = [n for n, alts in (("author", ("author", "editor")), ("title", ("title",)),
                                         ("year", ("year", "date"))) if not any(fields.get(a) for a in alts)]
            if missing:
                problems.append((key, path, ", ".join(missing)))
    return entries, dups, problems


def log_findings(log_path, root):
    with open(log_path, encoding="utf-8", errors="ignore") as fh:
        lines = fh.read().splitlines()
    stack, overfull, other = [], [], []
    for i, line in enumerate(lines):
        m = OVERFULL.search(line)
        if m:
            pts = float(m.group(2))
            src = next((s for s in reversed(stack) if s.endswith(".tex")), "?")
            start = m.group(3) or m.group(5) or "?"
            snippet = ""
            if i + 1 < len(lines) and not lines[i + 1].startswith(("Overfull", "Underfull", "[", "(")):
                snippet = re.sub(r"\\[A-Za-z0-9]+/\S+\s*(?:\(-?\d+\)\s*)?|\[\]", "", lines[i + 1]).strip()[:80]
            sev = "major" if pts >= 15 else "moderate" if pts >= 5 else "minor"
            overfull.append((sev, pts, m.group(1) + "box", os.path.relpath(src, root) if src != "?" else src,
                             start, snippet))
        if re.search(r"(Reference|Citation) `[^']+' on page \d+ undefined|multiply defined|There were undefined", line):
            other.append(line.strip())
        # Track which file TeX is reading from its "(file" ... ")" nesting.
        for tok in re.finditer(r"\((\.{0,2}/?[^\s()]+\.(?:tex|sty|cls|cfg|def|clo|aux|bbl|toc|out|fd))|\(|\)", line):
            if tok.group(1):
                stack.append(os.path.normpath(os.path.join(root, tok.group(1))))
            elif tok.group(0) == "(":
                stack.append("(")
            elif stack:
                stack.pop()
    return overfull, other


def sentence_around(text, pos):
    start = max(text.rfind(". ", 0, pos), text.rfind("\n\n", 0, pos))
    end_candidates = [e for e in (text.find(". ", pos), text.find("\n\n", pos)) if e != -1]
    end = min(end_candidates) if end_candidates else len(text)
    return " ".join(text[start + 1:end + 1].split())


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("main", help="the document's main .tex file")
    ap.add_argument("--log", help="LaTeX log (default: <main>.log beside it)")
    ap.add_argument("--generated", nargs="*", default=[], help="directories of generated files to check for use")
    ap.add_argument("--cite-context", action="store_true", help="print each citation's sentence and cited title")
    ap.add_argument("--style", action="store_true", help="flag phrases from the technical-prose list")
    args = ap.parse_args()

    files, missing_inputs, root = active_files(args.main)
    rel = lambda f: os.path.relpath(f, root)
    serious = 0
    print(f"{len(files)} active .tex file(s) under {root}")

    if missing_inputs:
        print("\n## Included files not found")
        for f, name in missing_inputs:
            print(f"  {rel(f)}: {name}")

    print("\n## Placeholders")
    n = 0
    for f, i, line in read_lines(files):
        if PLACEHOLDER.search(line) and "\\newcommand" not in line:
            print(f"  {rel(f)}:{i}: {line.strip()[:100]}")
            n += 1
    serious += n
    print(f"  {n} found")

    # Labels and references.
    labels, refs = defaultdict(list), []
    full = {}
    for f in files:
        with open(f, encoding="utf-8", errors="ignore") as fh:
            full[f] = strip_comments(fh.read())
    for f, i, line in read_lines(files):
        for lab in LABEL.findall(line):
            labels[lab].append(f"{rel(f)}:{i}")
        for group in REF.findall(line):
            for r in group.split(","):
                refs.append((r.strip(), f"{rel(f)}:{i}"))
    dup_labels = {k: v for k, v in labels.items() if len(v) > 1}
    undefined = [(r, where) for r, where in refs if r and r not in labels and "#" not in r]
    print("\n## Labels and references")
    for k, v in dup_labels.items():
        print(f"  label {k} defined {len(v)}x: {', '.join(v)}")
    for r, where in undefined:
        print(f"  {where}: \\ref to undefined label {r}")
    serious += len(undefined)
    if not dup_labels and not undefined:
        print("  none")

    # Bibliography.
    bib_paths = []
    for f, text in full.items():
        for group in BIBS.findall(text):
            for b in group.split(","):
                p = resolve(b, [root, os.path.dirname(f)], ext=".bib")
                if p:
                    bib_paths.append(p)
                else:
                    print(f"\n  bibliography {b.strip()} named in {rel(f)} not found")
    entries, dups, problems = parse_bib(sorted(set(bib_paths)))
    cites = []  # (key, file, offset)
    for f, text in full.items():
        for m in CITE.finditer(text):
            for k in m.group(1).split(","):
                if k.strip() and k.strip() != "*":
                    cites.append((k.strip(), f, m.start()))
    cited = {k for k, _, _ in cites}
    print(f"\n## Bibliography ({len(entries)} entries in {len(set(bib_paths))} file(s), {len(cited)} keys cited)")
    missing_keys = sorted(cited - set(entries)) if bib_paths else []
    for k in missing_keys:
        print(f"  cited but not in any .bib: {k}")
    for k, path in dups:
        print(f"  duplicate key {k} in {rel(path)}")
    for k, path, what in problems:
        flag = "" if k in cited else " (not cited)"
        print(f"  {k}: missing {what}{flag}")
    uncited = sorted(set(entries) - cited)
    if uncited:
        print(f"  {len(uncited)} entries never cited (harmless with BibTeX; check for leftovers): "
              + ", ".join(uncited[:15]) + (" ..." if len(uncited) > 15 else ""))
    serious += len(missing_keys)

    if args.cite_context:
        print("\n## Citation context (read each: does the cited work support this sentence?)")
        for k, f, pos in cites:
            title = entries.get(k, {}).get("title", "(not in .bib)")
            author = entries.get(k, {}).get("author", entries.get(k, {}).get("editor", ""))
            first = author.split(" and ")[0].split(",")[0].strip() if author else "?"
            line_no = full[f].count("\n", 0, pos) + 1
            print(f"  [{k}] {first}: {title[:90]}")
            print(f"      {rel(f)}:{line_no}: {sentence_around(full[f], pos)[:220]}")

    log = args.log or os.path.splitext(args.main)[0] + ".log"
    print(f"\n## Log ({rel(log) if os.path.exists(log) else 'not found: ' + log})")
    if os.path.exists(log):
        if os.path.getmtime(log) < max(os.path.getmtime(f) for f in files):
            print("  WARNING: log is older than the sources; rebuild before trusting this section")
        overfull, other = log_findings(log, root)
        counts = Counter(o[0] for o in overfull)
        print(f"  overfull boxes: {counts.get('major', 0)} major (>=15 pt), "
              f"{counts.get('moderate', 0)} moderate (5-15 pt), {counts.get('minor', 0)} minor (<5 pt)")
        for sev, pts, box, src, line, snippet in sorted(overfull, key=lambda o: -o[1]):
            if sev != "minor":
                print(f"    {sev:8s} {pts:6.1f} pt {box} {src}:{line}  {snippet}")
        for line in other:
            print(f"  {line}")
        serious += counts.get("major", 0) + sum("undefined" in o for o in other)

    for d in args.generated:
        print(f"\n## Generated files in {d} that the document never refers to")
        alltext = "\n".join(full.values())
        unused = []
        for name in sorted(os.listdir(d)):
            stem = os.path.splitext(name)[0]
            if os.path.isfile(os.path.join(d, name)) and stem not in alltext:
                unused.append(name)
        print("  " + ("\n  ".join(unused) if unused else "none"))

    if args.style:
        print("\n## Style (reread each sentence; see technical-prose)")
        pat = re.compile("|".join(STYLE), re.IGNORECASE)
        n = 0
        for f, i, line in read_lines(files):
            for m in pat.finditer(line):
                print(f"  {rel(f)}:{i}: '{m.group(0)}' in: {line.strip()[:100]}")
                n += 1
        print(f"  {n} found")

    print(f"\n{serious} serious finding(s) (placeholders, missing keys, undefined references, major overfull boxes)")
    return 1 if serious else 0


if __name__ == "__main__":
    sys.exit(main())
