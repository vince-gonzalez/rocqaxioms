# rocqaxioms

Source-only axiom readers for four proof libraries. No build, no toolchain, no install.
Point them at a checkout and they answer.

```
python rocq_axioms.py  /path/to/rocq/theories
python agda_axioms.py  /path/to/agda-stdlib
python afp_axioms.py   /path/to/afp
python isa_strip.py    /path/to/isabelle
```

## The finding

Every axiom census conflates two different claims, and reports one number.

A **mathematical assumption** is something the library genuinely relies on: excluded
middle, choice, functional extensionality, proof irrelevance.

An **interface obligation** is a `Parameter` or `Hypothesis` inside a `Module Type` or a
`Section`. It is discharged when the module is instantiated or the section closes. The
library does not assume it. It requires it of a caller.

A census that counts both reports a library assuming several hundred things it does not
assume. These readers track depth so interface obligations can be excluded rather than
guessed at.

That distinction is the result. It is not a detail of the implementation.

## Why it matters now

AI systems are increasingly trained and evaluated on the question of what a formal result
depends on. When the label merges a mathematical assumption with an interface obligation,
the model is being graded against a number that means two things at once.

## Published

Cross-foundation census, CC-BY-4.0, concept DOI **10.5281/zenodo.22148932**, with every
corpus commit recorded so the numbers reproduce.

## Scope

Source-only by design. These do not build the libraries and do not need to. Everything
they report is recoverable from the text, which is what makes the census reproducible from
a pinned commit rather than from a working environment.
