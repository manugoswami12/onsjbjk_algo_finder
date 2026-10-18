# Data used by the project (included, so nothing has to be downloaded)

Both folders are kept exactly as they were analysed. Files are stored byte for byte: the root `.gitattributes` turns
off line-ending conversion for `data/`.

| Folder | What it is | Source | Licence |
|---|---|---|---|
| `TheAlgorithms-Python/` | The code the system **learns from**: 1736 files, every algorithm of TheAlgorithms/Python | https://github.com/TheAlgorithms/Python at commit `e1a2a8b016001309a73d5fec4818c35cca139795`. Copied without its `.git` folder and its `.gitattributes`, which is git metadata only. | MIT: see `TheAlgorithms-Python/LICENSE.md` |
| `rosetta/Task/` | The code the system is **tested on** (never learned from): the 39 tasks in Python, C, Common Lisp and Haskell. It contains the 450 held-out files. | Rosetta Code, via https://github.com/acmeism/RosettaCodeData at commit `1d475861d7141ef2fafff293d9339f56e4b0f5db`. Only these four languages are copied. | GNU Free Documentation License 1.2 (Rosetta Code content), see below |

Rosetta Code content is from https://rosettacode.org and is available under the GNU Free Documentation License 1.2
(https://www.gnu.org/licenses/old-licenses/fdl-1.2.html). The files are copied unmodified, and each sits under its
task and language folder, as in RosettaCodeData.

The source code in these folders is **only read, never executed**: the system turns it into Prolog and runs that.
