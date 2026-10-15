# AP8 validation and handover

## Delivery identity

AP8 is an additive, opt-in **conservative audit**, not a replacement for the AP7 60/60 Windows baseline. It deliberately retains exact AST export and AP7 recognition semantics. The AP8 enhancements are separated into `audit_ast.pl`, `audit_rules.pl`, `audit_classify.pl` and `test_audit_recognition.py`.

## Commands (Windows CMD, within `semgrep_prolog_poc`)

```cmd
RUN_AP8_ACCEPTANCE.cmd
RUN_AUDIT.cmd examples\interleaved_sort_hash.py
RUN_AUDIT.cmd examples\audit_renamed.py
RUN_AUDIT.cmd examples\audit_wrong_bounds.py
RUN_AUDIT.cmd examples\audit_dead_hash.py
RUN_AUDIT.cmd examples\audit_premature_return.py
RUN_AUDIT.cmd examples\audit_interrupt.py
```

`RUN_AP6_ACCEPTANCE.cmd`, `RUN_THREADS.cmd`, `RUN_MULTI.cmd`, `RUN_DEMO.cmd` all remain supported. The Python CLI also supports `--audit` and `--ast-json <path>` for replay.

## Required outcomes

| Case | Strict audit expectation | Legacy AP7 status |
|---|---|---|
| Original interleaved example | Two `audited_structural` instances + `INTERLEAVED_AUDITED` | Two candidates + INTERLEAVED_WITH |
| Renamed variables, new base | Same two strict audited instances | Two candidates |
| Inner range `len(a)-i-2` | `unverified: bubble_sort` with `loop_bounds_not_established`; hash audited; no audited relation | May still report bubble candidate |
| Recurrence inside `if False` | Rolling hash **not audited**, diagnostic `update_not_direct_inner_statement` | May still report candidate |
| Top-level return before loop | Neither structural thread audited | May still report candidates |
| Unconditional `break` | Neither structural thread audited | May still report candidates |
| Binary search | `legacy_candidate` (unchanged matching logic) | Original AP7 candidate preserved |

## Test status / limitations

In this build environment Semgrep and SWI-Prolog executables are not installed, so actual Prolog and live Semgrep acceptance MUST be run on the office Windows PC. Offline tests validate CLI, Python fixture construction, exact exporter parity and structural test contracts. Do not freeze AP8 until all no-skip Windows tests pass, including live positive and adversarial negatives.

The audit deliberately calls unsupported equivalent loop variants `unverified`; that is not proof of absence. `audited_structural` does not guarantee correct sorting, absence of alias effects, general reachability or mathematical equivalence.

## Provenance

The file `tests/fixtures/ap8_actual_semgrep_negative_source.json` is copied from AP7's `out/ast.json` and corresponds to the earlier deliberately wrong-accumulator test. The synthetic mutation harness changes one identifier to create a positive control and generates other negative controls. This file is **not** falsely described as live positive evidence. Live Semgrep Windows tests reparse `.py` source files independently.
