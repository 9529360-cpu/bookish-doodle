# Benchmark Solver Rules

This repository is a training harness. When solving a case:

1. Read only the candidate-safe case brief and the pinned upstream checkout before forming the initial diagnosis.
2. Do not search for, open, or infer the historical fix PR before the candidate solution is frozen and evaluated.
3. Treat the pinned upstream repository as the source of truth. Read its repository instructions before editing.
4. Preserve the upstream working tree and never push to the upstream remote.
5. Define the user-visible contract, then trace ownership across state, UI/API, data, async/runtime, and delivery layers that actually participate.
6. Form at most three falsifiable hypotheses and run the cheapest discriminating probe first.
7. Before each production patch, state the expected mechanism and what observation would prove or disprove it.
8. Add or identify a regression test that fails for the original mechanism and passes for the candidate fix when practical.
9. Run the strongest practical repository-native validation. Record anything not run and why.
10. Capture the final diff and evidence before the curator reveals the historical fix.

A benchmark is not passed because the candidate patch resembles upstream. It passes when the contract is explained, the actual mechanism is repaired, regression risk is controlled, and the evidence supports the completion claim.
