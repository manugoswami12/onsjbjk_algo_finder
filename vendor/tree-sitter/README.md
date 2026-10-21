# tree-sitter, kept exactly as tested

The project reads source code with [tree-sitter](https://tree-sitter.github.io): Python, C, Rust, Java, R, Common Lisp,
Haskell and Prolog. Everything it needs from tree-sitter is kept here. A change upstream cannot change the results, and
the install works without internet.

**Install, offline** (from the repository root):

```
python vendor/tree-sitter/install_offline.py
```

This does three things:
- installs `tree-sitter` 0.26.0 and `tree-sitter-language-pack` 1.22.1 from `wheels/`;
- copies the 8 grammars, prebuilt for your computer, into the language pack's cache folder;
- checks every file against `SHA256SUMS`.

It works on Windows x86-64, macOS (Apple silicon and Intel) and Linux x86-64, with Python 3.10–3.14. On another
platform, use the online install in the root README, which installs the same pinned versions.

| Folder or file | What it is |
|---|---|
| `wheels/` | The exact pip packages, from PyPI. Each one's sha256 was checked against PyPI when it was downloaded. |
| `parsers/<platform>/` | The 8 prebuilt grammar libraries. They are extracted from the language pack's official v1.22.1 release bundles (sha256 checked against `parsers.json`). The Linux ones are byte-identical to the ones every test here ran with. |
| `parsers.json` | The language pack's v1.22.1 release manifest: bundle URLs and their sha256. |
| `source/tree_sitter-0.26.0.tar.gz` | Source of py-tree-sitter, including the tree-sitter C library (PyPI sdist). |
| `source/tree_sitter_language_pack-1.22.1.tar.gz` | Source of the language pack's Python binding (PyPI sdist). |
| `source/tree-sitter-language-pack-v1.22.1-core.tar.gz` | The language pack's Rust core, its grammar list with each grammar's repository and commit (`sources/language_definitions.json`), its licence and its attributions. Taken from github.com/xberg-io/tree-sitter-language-pack at tag v1.22.1. |
| `source/grammars/tree-sitter-<language>-<commit>.tar.gz` | The source of each of the 8 grammars, at the exact commit the release was built from (`grammar.js`, `src/parser.c`, licence). |
| `SHA256SUMS` | The sha256 of every file here. |

Grammar commits:

| Language | Repository | Commit |
|---|---|---|
| C | github.com/tree-sitter/tree-sitter-c | b780e47fc780ddc8da13afa35a3f4ed5c157823d |
| Common Lisp | github.com/theHamsta/tree-sitter-commonlisp | 32323509b3d9fe96607d151c2da2c9009eb13a2f |
| Haskell | github.com/tree-sitter/tree-sitter-haskell | 97288e585b0bd44199720280d067fa35bacd81ff |
| Java | github.com/tree-sitter/tree-sitter-java | e10607b45ff745f5f876bfa3e94fbcc6b44bdc11 |
| Prolog | github.com/Rukiza/tree-sitter-prolog | c246cf2bf36590a3cb4de380205376d3c46208e8 |
| Python | github.com/tree-sitter/tree-sitter-python | 26855eabccb19c6abf499fbc5b8dc7cc9ab8bc64 |
| R | github.com/r-lib/tree-sitter-r | 58a22794466c0fc15b0d3b40531db751593721e8 |
| Rust | github.com/tree-sitter/tree-sitter-rust | 77a3747266f4d621d0757825e6b11edcbf991ca5 |

Licences: each component keeps its own licence, included in its archive.
- tree-sitter, the language pack and seven of the grammars are under the MIT licence.
- The Prolog grammar is under the ISC licence.
