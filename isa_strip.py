#!/usr/bin/env python3
r"""Strip Isabelle comments, documentation and string literals properly.

Isabelle comments NEST:  (* outer (* inner *) still outer *)

A non-greedy regex closes the outer comment at the inner comment's terminator
and hands back the remainder as live code. That is how a commented-out block
containing `sorry` gets reported as an admitted proof in a refereed archive.
Depth counting is the only thing that reads this correctly.

Also removed:
  \<open> ... \<close>   text cartouches -- Isabelle's documentation syntax, and
                        where most prose discussing `sorry` actually lives
  "..."                 string literals -- one AFP entry searches HOL.thy for
                        the literal word "sorry" as a test of its string matcher
"""
from __future__ import annotations

OPEN, CLOSE = "(*", "*)"
COPEN, CCLOSE = "\\<open>", "\\<close>"


def strip(text: str) -> str:
    out = []
    i, n = 0, len(text)
    depth = 0        # nested (* *)
    cart = 0         # nested \<open> \<close>
    in_str = False
    while i < n:
        if not in_str and text.startswith(OPEN, i):
            depth += 1
            i += 2
            continue
        if depth and text.startswith(CLOSE, i):
            depth -= 1
            i += 2
            out.append(" ")
            continue
        if depth:
            i += 1
            continue
        if text.startswith(COPEN, i):
            cart += 1
            i += len(COPEN)
            continue
        if cart and text.startswith(CCLOSE, i):
            cart -= 1
            i += len(CCLOSE)
            out.append(" ")
            continue
        if cart:
            i += 1
            continue
        c = text[i]
        if c == '"' and (i == 0 or text[i - 1] != "\\"):
            in_str = not in_str
            out.append(" ")
            i += 1
            continue
        out.append(" " if in_str else c)
        i += 1
    return "".join(out)
