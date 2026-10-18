# AP11 Detailed Pseudocode, Activity Classes and Critical Logic

## Pseudocode
```python
# 0. Preflight
frozen = locate_sibling('semgrep_prolog_poc')
assert interfaces_exist(frozen, ['compile_reference', 'functions', 'capture', 'scan'])
assert store_is_inside_new_ap11_folder() and store_is_not_inside_frozen()
commit = git('rev-parse HEAD', cwd=corpus)
assert git_clean_tracked_checkout(corpus)

# 1. Intake
tracked_files = git_ls_files(categories)   # not rglob over untracked files
for file in round_robin_by_category(tracked_files):
    if global_function_limit_reached(): break
    if not regular_python_file_inside_checkout(file) or is_symlink(file):
        log_exclusion(file, 'unsafe'); continue
    if size(file) > source_size_limit:
        log_exclusion(file, 'oversize'); continue
    source_hash = sha256(bytes(file))

    # 2. Parse one source file, do not import it
    try:
        with new_temporary_directory(inside=AP11):
            ast_file = existing_AP10_semgrep_capture(file)
            ast_hash = sha256(bytes(ast_file))
            tree = existing_AP9_strict_load(ast_file)
            function_descriptors = list(existing_AP9_functions(tree))

            # 3. Select supported unambiguous functions only
            for function in function_descriptors:
                if function_limit_reached(): break
                label = deterministic_safe_label(commit, file, function)
                if db_record_exists(label):
                    verify_exact_immutable_source_ast_and_clause_hashes()
                    continue
                if duplicate_function_name_in_single_AST(function):
                    record_skip_and_reason(); continue

                # 4. Compile, never handwrite algorithm-specific Prolog
                try:
                    clause = existing_AP9_compile_reference(
                        ast_file, label, function.name, 'body', ordinal=0)
                    structural_fingerprint = sha256(clause_without_label)
                    atomic_publish_if_new(AP11_store / 'refs' / (label + '.pl'))
                    sqlite_insert_immutable_record(status='generated', review='unreviewed')
                except expected_error as error:
                    sqlite_insert_record(status='error', reason=str(error))
    except expected_parser_error as error:
        sqlite_insert_file_error(source_hash, error)

# 5. Review by a human, no autodetected approved labels
for reference in sqlite_unreviewed_references():
    if source_identity_and_function_verified(reference):
        set_review_status(reference, 'approved')
    else:
        set_review_status(reference, 'rejected')

# 6. Unknown-code scan, frozen AP10 alone performs recognition
entries = sqlite_select_approved_by_category(max_count=30)
with new_temporary_directory(inside=AP11):
    verify_sha256_for_each_clause(entries)
    create_ap10_compatible_catalog_and_clause_copies(entries)
    # ap10.scan creates one validated bundle and invokes original SWI-Prolog rules
    output = existing_AP10_scan(temporary_catalog, unknown_python_file)
print(output + structural_only_warning)

# 7. Acceptance
run_offline_tests()
run_windows_ap10_acceptance_before_and_after()
run_holdout_positive_and_negative_evaluation()
```

## Activity / module mapping
| Type of activity | Module | Inputs | Output |
|---|---|---|---|
| User input / command dispatch | `cli.py` + `RUN_AP11.cmd` | flags, paths, labels | command result or explicit error |
| Git and filesystem environment | `source.py` + `RUN_AP11_DOWNLOAD.cmd` | pinned Git tree | commit, safe tracked file paths |
| Existing parser + compiler interface | `bridge.py` | sibling AP9/AP10 | unchanged compiler and scanner functions |
| Program logic / iteration / conversion | `ingest.py` | Semgrep AST and function descriptors | generated `.pl` clauses |
| File save / data store | `database.py`, `ingest.py` | checksums, provenance, status | SQLite rows and immutable `.pl` |
| Query / Prolog / output display | `recognize.py` | reviewed SQLite references, target Python | AP10 evidence or UNKNOWN |
| Tests / validation | `tests/test_ap11.py` | real captured AST and temporary Git repo | offline regression results |

## Critical logic table
Definition: a boundary is **critical** if **(1)** it interfaces with the environment/another program, **or (2)** it is a base for more than two subsequent activities.

| Critical logic | Which criterion | Failure mode | Test / safeguard |
|---|---|---|---|
| Git revision / safe path intake | 1,2 | untracked/source changed, symlink escape, wrong upstream commit | clean-worktree gate; Git-tracked list; path checks; SHA |
| Semgrep OCaml AST capture | 1,2 | malformed/partial AST, parser timeout | use frozen bounded capture, strict JSON decoder, explicit parse error |
| AP9 function discovery and compiler | 1,2 | wrong function, unsupported body, binding/AST loss | use exact unchanged API; duplicate-name skip; real AST fixture replay |
| Prolog clause publishing | 1,2 | injection, partial output, overwrite after crash | only AP9 emits clauses; atomic rename, checksum recheck, immutable ID |
| SQLite transaction / review | 1,2 | duplicate identity, silent label promotion, partial catalog | PRIMARY KEY; transactions; approval only by explicit command |
| AP10 bundle + SWI-Prolog process | 1,2 | static predicate redefinition, timeouts, excessive search | call unchanged bundler and scan; bounded first 30 references |
| Counts and testing / report | 1,2 | unverifiable coverage claims or concealed errors | counts separated, holdout positives/negatives, AP10 acceptance re-run |

## Known honest limitations
* AP9's `functions()` does not recognize every Python function encoding in every Semgrep version. An unsupported file is a recorded error, never a silent recognized algorithm.
* The provisional reference label combines filename and function identifier. Both are metadata from upstream, **not evidence of what the code mathematically computes**.
* The matcher uses reference body patterns; a complex unknown implementation that computes the same answer differently may remain `UNKNOWN`.
* SQLite structural hashes do not prove semantic equivalence. They are fingerprints for retrieval and duplicate investigation only.
* The pilot's 30 patterns do not guarantee all categories are represented by successful compiles. Review category counts before claiming breadth.
* Re-ingestion of a recorded error preserves the failure record; fixing/transient-error retries need explicit curation or a fresh AP11 store. Good data are not overwritten automatically.
