#!/usr/bin/env python3
r"""What does the Archive of Formal Proofs assume, and what is unfinished in it?

    python afp_axioms.py /path/to/afp/thys

The AFP is a curated, refereed archive: every entry is built and checked by the
Isabelle release process. That makes two questions worth asking of it that are
not worth asking of an ordinary library.

  `axiomatization`  Isabelle's way of asserting something without proof. An AFP
                    entry that axiomatizes is adding to the trusted base of
                    anything that imports it. Isabelle/HOL's own axioms are not
                    in scope here; this counts what the ARCHIVE adds on top.

  `sorry`           an admitted proof. Isabelle accepts it, marks the result,
                    and carries on. A `sorry` anywhere upstream means a theorem
                    that looks proved is not, which is exactly the failure mode
                    a provenance tool exists to catch, and exactly the one that
                    a green build does not reveal.

Comments are stripped before counting, because "sorry" and "axiomatization"
both appear in prose discussing them, and counting those would inflate every
number here. Occurrences inside string literals are left, which biases the
counts slightly upward -- the report says which files so they can be read.
"""
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from isa_strip import strip as isa_strip

COMMENT = re.compile(r"\(\*.*?\*\)", re.S)
# a theory header: theory NAME imports A B C begin
IMPORTS = re.compile(r"\btheory\s+([\w.']+)\s+imports\s+(.*?)\bbegin\b", re.S)
AXIOMATIZATION = re.compile(r"(?<![\w'])axiomatization(?![\w'])")
SORRY = re.compile(r"(?<![\w'])sorry(?![\w'])")
OOPS = re.compile(r"(?<![\w'])oops(?![\w'])")
CONSTS = re.compile(r"^\s*consts(?![\w'])", re.M)


def main() -> None:
    root = Path(sys.argv[1])
    files = sorted(root.rglob("*.thy"))
    print(f"   {len(files):,} theory files under {root}")

    ax_files, sorry_files, oops_files, consts_files = {}, {}, {}, {}
    entries = Counter()
    total = Counter()

    for p in files:
        raw = p.read_text(encoding="utf-8", errors="replace")
        # only pay for the depth-counting strip when a keyword is present
        if any(k in raw for k in ("sorry", "axiomatization", "oops", "consts")):
            code = isa_strip(raw)
        else:
            code = raw
        rel = p.relative_to(root)
        entry = rel.parts[0] if len(rel.parts) > 1 else "(top)"
        entries[entry] += 1

        n_ax = len(AXIOMATIZATION.findall(code))
        n_sorry = len(SORRY.findall(code))
        n_oops = len(OOPS.findall(code))
        n_consts = len(CONSTS.findall(code))
        total["axiomatization"] += n_ax
        total["sorry"] += n_sorry
        total["oops"] += n_oops
        total["consts"] += n_consts
        if n_ax:
            ax_files[str(rel)] = n_ax
        if n_sorry:
            sorry_files[str(rel)] = n_sorry
        if n_oops:
            oops_files[str(rel)] = n_oops
        if n_consts:
            consts_files[str(rel)] = n_consts

    print(f"   {len(entries):,} entries")
    print()
    print(f"   {'construct':<18}{'occurrences':>13}{'files':>8}{'entries':>9}")
    print("   " + "-" * 50)
    for name, d in (("axiomatization", ax_files), ("sorry", sorry_files),
                    ("oops", oops_files), ("consts", consts_files)):
        ents = {f.split("/")[0].split("\\")[0] for f in d}
        print(f"   {name:<18}{total[name]:>13,}{len(d):>8,}{len(ents):>9,}")

    for title, d in (("entries that axiomatize", ax_files),
                     ("files containing sorry", sorry_files)):
        print()
        print(f"   {title}")
        print("   " + "-" * 66)
        for f, n in sorted(d.items(), key=lambda kv: -kv[1])[:18]:
            print(f"   {n:>4}  {f}")
        if len(d) > 18:
            print(f"         ... and {len(d)-18} more")


if __name__ == "__main__":
    main()
