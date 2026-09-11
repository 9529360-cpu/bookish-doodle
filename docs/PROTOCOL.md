# Historical Bug Benchmark Protocol

## 1. Goal

Use mature public repositories as an external reality check for the `runtime-regression-debugger` Skill. The objective is not to memorize upstream patches. It is to test whether the Skill can recover repository truth, locate ownership, form falsifiable hypotheses, make a minimal compatible change, and prove the user-visible contract.

## 2. Two-session rule

For a meaningful blind run, separate **curation** from **solving**.

- The curator may inspect the issue, merged fix, review discussion, and final tests to choose a case and pin a buggy base SHA.
- The solver starts in a fresh conversation/agent session that receives only the case brief and the pinned repository checkout.
- Ground-truth PR numbers and diffs are intentionally not stored in the public candidate case JSON.
- If the same model/session has already inspected the historical fix, that case can still test tooling and validation, but it no longer counts as a blind reasoning benchmark.

## 3. Case selection

Prefer cases that have:

- a reproducible user/operator-visible failure;
- an exact buggy base commit that remains fetchable;
- a non-trivial ownership or lifecycle mistake rather than a typo;
- a merged historical fix and useful review/test evidence for post-hoc comparison;
- a validation boundary that is practical on disposable local compute;
- no dependence on private services, private data, or unavailable credentials.

Avoid cases whose only challenge is dependency installation, generated files, or obscure project-specific trivia.

## 4. Candidate workflow

1. Run `python3 scripts/bench.py audit`.
2. Run `python3 scripts/bench.py brief <case-id>` and give only that output to the solver.
3. Run `python3 scripts/bench.py prepare <case-id>` to create the pinned checkout under `.bench/worktrees/`.
4. Let the solver inspect repository instructions, active callers, tests, manifests, history, and relevant current docs.
5. Freeze the candidate once it has a diagnosis, patch, regression proof, and validation evidence.
6. Run `python3 scripts/bench.py status <case-id>` and `capture <case-id>`.
7. Only now let the curator compare the candidate with the historical fix and review discussion.

## 5. Validation policy

Validation is evidence, not ceremony. Cases may provide `smoke`, `focused`, and `full` command tiers. Commands are argument arrays and are executed without a shell.

The harness does **not** automatically install dependencies. Setup commands are printed by `doctor`; running them is an explicit choice because upstream installs can be slow, download large artifacts, start containers, or require local services.

A solver may use a stronger or more targeted repository-native command than the case file suggests. Record the exact command and result.

## 6. Scoring rubric

Score a run out of 100:

- **35 — Contract and correctness:** fixes the actual user-visible failure and preserves nearby invariants.
- **20 — Diagnosis quality:** identifies the real owner/mechanism with evidence instead of patching the symptom.
- **20 — Regression proof:** adds or identifies a test/probe that exercises the failure mechanism, including ordering/lifecycle behavior when relevant.
- **15 — Patch quality:** minimal compatible change, no duplicate authority, no unrelated churn, appropriate failure handling.
- **10 — Validation and claims:** runs the strongest practical checks and does not claim more than was proven.

Similarity to the historical patch is not a scoring category. A different implementation can score higher if it is more correct and better evidenced.

## 7. Learning loop

After evaluation, write a short learning record outside the upstream checkout:

- observed failure mechanism;
- assumptions the solver got right or wrong;
- evidence that changed the diagnosis;
- validation gaps;
- whether the historical fix revealed a generalizable engineering pattern;
- one concise Skill change, if any, that would improve future unrelated tasks.

Do not copy upstream source code or case-specific magic strings into the Skill. Generalize the lesson into ownership, lifecycle, compatibility, failure-mode, testing, or rollout guidance.

## 8. Cost controls

The benchmark repo has no automatic Actions runner. Use local/disposable compute and start with the cheapest evidence boundary. Do not run a full monorepo test suite merely because it exists. Escalate from static inspection and focused tests to integration/system tests when the risk or mechanism requires it.
