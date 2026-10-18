# AP12 design -> detailed Python pseudocode -> activities

```python
def all_tracked_python(corpus):
    commit = ap11.revision(corpus)                # verify clean pinned checkout
    ap11.verify_origin(corpus)
    raw_names = git_ls_files_null_delimited(corpus)
    for relative in sorted(name for name in raw_names if name.endswith('.py')):
        path = ap11.source_path(corpus, relative) # rejects escapes and symlinks
        yield commit, relative, sha256(read_bytes(path))

def ingest_all(corpus, store, max_files=None):
    # AP11 itself stays unchanged; re-use frozen compile_reference and AP11 DB helpers.
    manifest = list(all_tracked_python(corpus))
    for index, source in enumerate(manifest):
        if max_files is not None and index >= max_files: break
        if ledger_has_verified_success(source) and ap11_patterns_are_verified(source):
            print_progress('PRESENT', source); continue
        capture_ast_via_existing_semgrep_api(source)  # no imports or execution
        discover_functions_using_existing_semgrep_ast_reader()
        for function in discovered_functions:
            if AP11_row_exists: validate_sha_and_generated_clause()
            else: compile_using_frozen_AP9_and_ap11_add_immutable_row()
        if no_functions_or_semgrep_error: record_AP11_file_marker()
        analysed = fallback.analyze_source(source_as_text)
        routes = fallback.route_live(analysed)  # SWI run, no source execution
        facts = fallback.facts_from(analysed)
        store_separately_with_hashes_and_immutable_filepath(facts, routes)
        save_checkpoint_only_when_both_attempts_and_verifications_complete()
        print_progress()
    verify_and_report(source_manifest_again(), rows_and_file_hashes())

def scan_auto(source, explicit_review_policy):
    strict = ap11.scan(source, review_policy=explicit_review_policy)
    matched_functions = parse_AP10_THREAD_function_names(strict)
    if any_not_matched_or_no_references:
        analyses = fallback.analyze_source(source)
        routes = fallback.route_live(analyses)
        for function not in matched_functions:
            report(CANDIDATE_BRANCHES=routes, NOT_ALGORITHM_PROOF=True)
    return strict, fallback_results
```

## Rational activity classification
| Activity type | Operations | Module |
|---|---|---|
| Input/environment | Git tracked source enumeration; pinned revision; limits | `ap12/full_ingest.py` |
| Parse/convert | frozen Semgrep compiler; existing static fallback | `ap12/full_ingest.py`, existing public APIs |
| File save/database | immutable AP11 patterns; separate AP12 SQLite and `.pl` facts | `ap12/storage.py` |
| Recognition/query | frozen strict scan; automatic fallback routing for unmatched functions | `ap12/scan_auto.py` |
| Verify/audit | compare manifest and ledger; validate all SHA-256; explain gaps | `ap12/verify.py` |
| User CLI/display | one CMD full runner, one CMD hybrid scanner | `RUN_AP12_FULL.cmd`, `RUN_AP12_SCAN.cmd` |
| Tests | mocked frozen capture; real standalone fallback extractor; provenance checks | `tests/test_ap12.py` |

Do not silently convert source names or repository labels into an algorithm identity. Preserve observed facts, candidate branches, and reasons for unknowns. The design is deliberately bounded.

## Added conservative interval variant evidence (independent AP12-only enhancement)
When the v0.1 fallback says UNKNOWN for a bisect-style function, AP12's `interval_evidence.py` looks for a while-loop bounded by named `left/right` indices; midpoint calculation; an indexed input-sequence element compared with a distinct input target, optionally through a single assigned local; condition-controlled lower/upper updates in the appropriate directions; and a returned bound or saved midpoint. Only when **all** are present, it adds `bounded_indexed_interval_lookup` to the observation set. The separate AP12 Prolog router treats this as one additional reason to route to the `interval_lookup` family. It is NOT a proof of sortedness, duplicate semantics, return correctness or mathematical invariants. The frozen 11-case router is not edited.

New branch-to-category selection: `comparison_driven_reordering` and `sequence_rearrangement` -> candidate `sorts` references; `indexed_lookup` and `interval_lookup` -> candidate `searches` references. This narrows *which frozen strict templates are attempted*, not what counts as a valid strict match. Per scan, the unchanged AP11 100-reference limit is still enforced and reported as truncated when applicable.
