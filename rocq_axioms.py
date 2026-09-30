#!/usr/bin/env python3
r"""Where does the Rocq standard library spend its axioms?

    python rocq_axioms.py /path/to/stdlib/theories

Rocq is constructive by default. Excluded middle, choice, functional
extensionality and proof irrelevance are not available unless a file asks for
them, and asking is a visible act: `Require Import` of a module that declares
them. That makes the question "what does this result assume" answerable from
the source, without building anything.

WHAT COUNTS AS AN AXIOM

Only a top-level `Axiom`. `Parameter` and `Hypothesis` inside a `Module Type`
or a `Section` are discharged when the module is instantiated or the section
closes; they are interface obligations, not assumptions the library makes. A
census that counts them reports a library assuming several hundred things it
does not assume. Depth is tracked so they can be excluded rather than guessed
at.

WHAT THIS DOES NOT DO

This is module-level, not theorem-level. A file that requires
`Logic.Classical` inherits the axiom whether or not any theorem in it uses
excluded middle, so the counts below are an upper bound on what actually rests
on the axiom. `Print Assumptions` answers the per-theorem question and needs a
built library; this answers the per-file one and needs only the source.
"""
from __future__ import annotations

import re
import sys
from collections import defaultdict, deque
from pathlib import Path

AXIOM = re.compile(r"^\s*Axiom\s+([A-Za-z_][A-Za-z0-9_']*)", re.M)
OPEN = re.compile(r"^\s*(Module\s+Type\b|Module\b|Section\b)", re.M)
CLOSE = re.compile(r"^\s*End\b", re.M)
# "Require Import A.B C." / "Require Export A." / "From X Require Import Y."
REQUIRE = re.compile(
    r"^\s*(?:From\s+([\w.]+)\s+)?Require\s+(?:Import|Export)?\s*([^.]*)\.",
    re.M)
COMMENT = re.compile(r"\(\*.*?\*\)", re.S)


def toplevel_axioms(text):
    """Axioms declared at depth 0, i.e. not inside a Module Type or Section."""
    depth = 0
    found = []
    events = []
    for m in OPEN.finditer(text):
        events.append((m.start(), +1, None))
    for m in CLOSE.finditer(text):
        events.append((m.start(), -1, None))
    for m in AXIOM.finditer(text):
        events.append((m.start(), 0, m.group(1)))
    for _pos, kind, name in sorted(events):
        if kind == 0:
            if depth == 0:
                found.append(name)
        else:
            depth = max(0, depth + kind)
    return found


def load(root: Path):
    files, text = {}, {}
    for p in sorted(root.rglob("*.v")):
        rel = p.relative_to(root)
        mod = ".".join(rel.with_suffix("").parts)
        files[mod] = p
        text[mod] = COMMENT.sub(" ", p.read_text(encoding="utf-8", errors="replace"))
    return files, text


def requires(text, known):
    """Modules this file requires, resolved against what exists."""
    out = set()
    for m in REQUIRE.finditer(text):
        prefix, body = m.group(1), m.group(2)
        for tok in body.replace("\n", " ").split():
            if not re.match(r"^[\w.]+$", tok):
                continue
            cands = [tok]
            if prefix:
                cands.append(prefix + "." + tok)
            # Rocq module paths drop the library root; match on any suffix
            for c in cands:
                tail = c.split(".")
                for k in known:
                    if k.split(".")[-len(tail):] == tail:
                        out.add(k)
    return out


def main() -> None:
    root = Path(sys.argv[1])
    files, text = load(root)
    known = set(files)
    print(f"   {len(files)} files under {root}")

    declares = {m: toplevel_axioms(t) for m, t in text.items()}
    roots = {m: a for m, a in declares.items() if a}
    total_axioms = sum(len(a) for a in roots.values())
    print(f"   {total_axioms} top-level Axiom declarations in {len(roots)} files")

    deps = {m: requires(t, known) for m, t in text.items()}

    # who reaches an axiom-declaring file
    reach = {}

    def visit(m, stack=()):
        if m in reach:
            return reach[m]
        if m in stack:
            return set()
        got = set(roots.get(m, ()) and [m] or [])
        for d in deps.get(m, ()):
            got |= visit(d, stack + (m,))
        reach[m] = got
        return got

    sys.setrecursionlimit(20000)
    for m in files:
        visit(m)

    touched = [m for m in files if reach[m]]
    print(f"   {len(touched)} of {len(files)} files "
          f"({len(touched)/len(files):.1%}) transitively require an axiom file")
    print()

    # which axiom source is inherited most widely
    below = defaultdict(set)
    for m in files:
        for r in reach[m]:
            below[r].add(m)
    print(f"   {'axiom-declaring file':<44}{'axioms':>7}{'files below':>13}")
    print("   " + "-" * 66)
    for r, users in sorted(below.items(), key=lambda kv: -len(kv[1])):
        print(f"   {r:<44}{len(roots[r]):>7}{len(users):>13}")
    print()
    print("   the axioms themselves, by file")
    for r in sorted(roots, key=lambda r: -len(below[r])):
        print(f"   {r}")
        print(f"      {', '.join(sorted(roots[r]))[:200]}")


if __name__ == "__main__":
    main()
