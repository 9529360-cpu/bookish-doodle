# Veteran Engineer Lab

Public, local-first benchmark harness for evaluating and evolving the `runtime-regression-debugger` skill against real historical bugs from mature open-source repositories.

The lab intentionally does **not** vendor Immich, Mattermost, Discourse, or other upstream repositories. Each case pins a buggy upstream commit and provides only a candidate-safe task brief. The solver works in a fresh checkout; the historical fix is inspected only after evaluation.

## Initial benchmark matrix

| Case | Upstream | Track | Difficulty |
| --- | --- | --- | --- |
| `immich-26979` | `immich-app/immich` | mobile navigation / reactive state | medium |
| `mattermost-37930` | `mattermost/mattermost` | startup ordering / async state hydration | hard |
| `discourse-42435` | `discourse/discourse` | browser history / infinite-scroll state | hard |

## Why local-first

This repository deliberately contains no benchmark GitHub Actions workflow. Preparing and validating cases is done on a developer machine, disposable VM, or other compute you explicitly choose, so the harness does not silently consume GitHub Actions minutes.

## Quick start

```bash
python3 scripts/bench.py audit
python3 scripts/bench.py list
python3 scripts/bench.py brief immich-26979
python3 scripts/bench.py doctor immich-26979
python3 scripts/bench.py prepare immich-26979
```

After the solver has made a candidate change in `.bench/worktrees/<case-id>`:

```bash
python3 scripts/bench.py status immich-26979
python3 scripts/bench.py validate immich-26979 --tier focused
python3 scripts/bench.py capture immich-26979
```

Some upstream suites require large dependency installs, databases, browsers, mobile SDKs, or containers. The harness never installs those automatically. Use `doctor` and the case metadata first, then opt into setup/validation commands explicitly.

## Benchmark rules

- Do not vendor upstream repositories into this repo.
- Pin every benchmark to an exact upstream base commit.
- Keep historical fix PRs and fix diffs out of candidate-visible case files.
- Use a separate curation session and solver session when you want a genuinely blind evaluation.
- Run upstream-native tests where practical; add the narrowest regression proof that demonstrates the contract.
- Score reasoning and evidence, not textual similarity to the historical patch.
- Record only generalized engineering lessons in the Skill; do not copy project-specific source code into it.
- Never push changes from benchmark worktrees to upstream repositories.
- Do not add automatic GitHub Actions benchmark runs unless the repository owner explicitly asks for them.

See [`docs/PROTOCOL.md`](docs/PROTOCOL.md) for the full curation, solving, validation, and learning loop.
