# Veteran Engineer Lab

Sandbox repository for evaluating and evolving the `runtime-regression-debugger` skill against real historical bugs in public open-source repositories.

Principles:
- Do not vendor upstream repositories into this repo.
- Pin every benchmark to an exact upstream base commit.
- Hide the upstream fix patch until after the candidate solution is evaluated.
- Run upstream-native tests where practical.
- Record only generalized engineering lessons, not project-specific source code, in the skill.
- Never push changes to upstream repositories from this harness.

Initial training track: `immich-app/immich`.
