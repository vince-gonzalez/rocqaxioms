#!/usr/bin/env python3
r"""What does the Agda standard library assume, and where?

    python agda_axioms.py /path/to/agda-stdlib/src

Agda's assumption is the `postulate`: a name given a type and no definition.
Its unsafe surface is wider than that -- `primTrustMe`, `unsafeCoerce`, and the
`TERMINATING` pragma each let something through the checker that the checker did
not establish.

WHY THIS LIBRARY IS THE ONE WORTH MEASURING

Agda has `{-# OPTIONS --safe #-}`, and the compiler enforces it: a module
declared safe may not postulate, may not use the unsafe primitives, and may not
import a module that is not itself safe. That last clause is the useful part.
It means the compiler has already computed the transitive answer, so a textual
analysis can be checked against ground truth rather than argued about.

Any file this reports as both `--safe` and reaching a postulate is a bug in
this script, not a finding about Agda. That check runs at the end and is the
only reason to trust the rest of the output.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

BLOCK = re.compile(r"\{-(?!#).*?-\}", re.S)      # {- ... -} but not pragmas
LINE = re.compile(r"(?<!-)--(?!\})[^\n]*")        # -- to end of line
IMPORT = re.compile(r"^\s*(?:open\s+)?import\s+([\w.']+)", re.M)
# "postulate" opens a block only when nothing follows it on the line.
# `postulate[_|->_]` is a legal function NAME in Agda, and \b matches between
# the "e" and the "[", so \b counts a definition as an assumption.
POSTULATE = re.compile(r"^[ \t]*postulate[ \t]*(?:$|--)", re.M)
OPTIONS = re.compile(r"\{-#\s*OPTIONS([^#]*)#-\}")
UNSAFE_TOKENS = ("primTrustMe", "unsafeCoerce", "TERMINATING")


def strip(text):
    """Remove comments so a word in prose is not read as code."""
    return LINE.sub(" ", BLOCK.sub(" ", text))


def load(root: Path):
    mods, raw, code = {}, {}, {}
    for p in sorted(root.rglob("*.agda")):
        mod = ".".join(p.relative_to(root).with_suffix("").parts)
        mods[mod] = p
        t = p.read_text(encoding="utf-8", errors="replace")
        raw[mod] = t
        code[mod] = strip(t)
    return mods, raw, code


def main() -> None:
    root = Path(sys.argv[1])
    mods, raw, code = load(root)
    print(f"   {len(mods)} modules under {root}")

    safe, opts = {}, {}
    for m, t in raw.items():
        o = " ".join(x.group(1) for x in OPTIONS.finditer(t))
        opts[m] = o
        safe[m] = "--safe" in o
    print(f"   {sum(safe.values())} declare --safe "
          f"({sum(safe.values())/len(mods):.1%})")

    posts = {m for m, c in code.items() if POSTULATE.search(c)}
    unsafe_prim = {m for m, c in code.items()
                   if any(tok in c for tok in UNSAFE_TOKENS)}
    print(f"   {len(posts)} modules postulate; "
          f"{len(unsafe_prim)} use primTrustMe / unsafeCoerce / TERMINATING")
    print()

    known = set(mods)
    deps = {}
    for m, c in code.items():
        deps[m] = {i for i in IMPORT.findall(c) if i in known}

    sys.setrecursionlimit(30000)
    reach = {}

    def visit(m, stack=()):
        if m in reach:
            return reach[m]
        if m in stack:
            return set()
        got = {m} if m in posts else set()
        for d in deps.get(m, ()):
            got |= visit(d, stack + (m,))
        reach[m] = got
        return got

    for m in mods:
        visit(m)

    touched = [m for m in mods if reach[m]]
    print(f"   {len(touched)} of {len(mods)} modules ({len(touched)/len(mods):.1%}) "
          f"transitively import a postulate")
    print()

    below = {}
    for m in mods:
        for r in reach[m]:
            below.setdefault(r, set()).add(m)
    print(f"   {'module that postulates':<52}{'safe?':>7}{'below':>7}")
    print("   " + "-" * 68)
    for r, users in sorted(below.items(), key=lambda kv: -len(kv[1])):
        print(f"   {r:<52}{('yes' if safe[r] else 'no'):>7}{len(users):>7}")

    # ---- the check that makes the rest trustworthy --------------------
    print()
    contradictions = [m for m in mods if safe[m] and reach[m]]
    if contradictions:
        print(f"   INSTRUMENT FAILS: {len(contradictions)} modules are --safe "
              f"yet reach a postulate. Agda forbids that, so this is my bug.")
        for m in contradictions[:10]:
            print(f"      {m}  ->  {', '.join(sorted(reach[m]))[:70]}")
    else:
        print("   CHECK PASSES: no --safe module reaches a postulate, which is "
              "what the Agda compiler guarantees.")


if __name__ == "__main__":
    main()
