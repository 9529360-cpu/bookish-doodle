#!/usr/bin/env python3
"""Local-first historical bug benchmark harness.

Standard-library only. It never pushes upstream, never executes shell strings, and never
installs dependencies automatically.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CASES_DIR = ROOT / "cases"
BENCH_DIR = ROOT / ".bench"
WORKTREES_DIR = BENCH_DIR / "worktrees"
RESULTS_DIR = ROOT / "results"
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
HIDDEN_BRIEF_KEYS = {"ground_truth", "ground_truth_pr", "oracle", "curation"}


class BenchError(RuntimeError):
    pass


def run(argv: list[str], cwd: Path | None = None, capture: bool = False) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(argv), file=sys.stderr)
    return subprocess.run(
        argv,
        cwd=str(cwd) if cwd else None,
        check=True,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )


def load_case(case_id: str) -> dict[str, Any]:
    if not ID_RE.fullmatch(case_id):
        raise BenchError(f"invalid case id: {case_id!r}")
    path = CASES_DIR / f"{case_id}.json"
    if not path.is_file():
        raise BenchError(f"case not found: {case_id}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BenchError(f"invalid JSON in {path}: {exc}") from exc
    validate_case(data, path)
    return data


def validate_command(value: Any, where: str) -> None:
    if not isinstance(value, dict):
        raise BenchError(f"{where} must be an object")
    cwd = value.get("cwd")
    argv = value.get("argv")
    if not isinstance(cwd, str) or not cwd:
        raise BenchError(f"{where}.cwd must be a non-empty string")
    if Path(cwd).is_absolute() or ".." in Path(cwd).parts:
        raise BenchError(f"{where}.cwd must stay inside the upstream checkout")
    if not isinstance(argv, list) or not argv or not all(isinstance(x, str) and x for x in argv):
        raise BenchError(f"{where}.argv must be a non-empty string array")


def validate_case(data: Any, path: Path) -> None:
    if not isinstance(data, dict):
        raise BenchError(f"{path} must contain a JSON object")
    required = ["schema_version", "id", "upstream_repo", "base_sha", "track", "difficulty", "contract", "runtime", "validation"]
    missing = [key for key in required if key not in data]
    if missing:
        raise BenchError(f"{path} missing keys: {', '.join(missing)}")
    if data["schema_version"] != 1:
        raise BenchError(f"{path}: unsupported schema_version {data['schema_version']!r}")
    if not isinstance(data["id"], str) or not ID_RE.fullmatch(data["id"]):
        raise BenchError(f"{path}: invalid id")
    if path.stem != data["id"]:
        raise BenchError(f"{path}: filename must match id")
    if not isinstance(data["upstream_repo"], str) or not REPO_RE.fullmatch(data["upstream_repo"]):
        raise BenchError(f"{path}: invalid upstream_repo")
    if not isinstance(data["base_sha"], str) or not SHA_RE.fullmatch(data["base_sha"]):
        raise BenchError(f"{path}: base_sha must be a 40-character lowercase SHA")
    runtime = data["runtime"]
    if not isinstance(runtime, dict) or not isinstance(runtime.get("working_directory"), str):
        raise BenchError(f"{path}: runtime.working_directory is required")
    bins = runtime.get("required_bins", [])
    if not isinstance(bins, list) or not all(isinstance(x, str) and x for x in bins):
        raise BenchError(f"{path}: runtime.required_bins must be a string array")
    validation = data["validation"]
    if not isinstance(validation, dict):
        raise BenchError(f"{path}: validation must be an object")
    for idx, command in enumerate(validation.get("setup", [])):
        validate_command(command, f"{path}: validation.setup[{idx}]")
    tiers = validation.get("tiers", {})
    if not isinstance(tiers, dict):
        raise BenchError(f"{path}: validation.tiers must be an object")
    for tier, commands in tiers.items():
        if tier not in {"smoke", "focused", "full"}:
            raise BenchError(f"{path}: unsupported validation tier {tier!r}")
        if not isinstance(commands, list):
            raise BenchError(f"{path}: validation.tiers.{tier} must be an array")
        for idx, command in enumerate(commands):
            validate_command(command, f"{path}: validation.tiers.{tier}[{idx}]")


def iter_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for path in sorted(CASES_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        validate_case(data, path)
        cases.append(data)
    return cases


def worktree(case: dict[str, Any]) -> Path:
    return WORKTREES_DIR / case["id"]


def safe_brief(case: dict[str, Any]) -> dict[str, Any]:
    allowed = [
        "schema_version", "id", "upstream_repo", "base_sha", "track", "difficulty",
        "contract", "symptoms", "reproduction", "runtime", "validation",
    ]
    brief = {key: case[key] for key in allowed if key in case and key not in HIDDEN_BRIEF_KEYS}
    validation = dict(brief.get("validation", {}))
    validation.pop("setup", None)
    brief["validation"] = validation
    return brief


def cmd_audit(_: argparse.Namespace) -> None:
    cases = iter_cases()
    if not cases:
        raise BenchError("no cases found")
    ids = [case["id"] for case in cases]
    if len(ids) != len(set(ids)):
        raise BenchError("duplicate case ids")
    print(f"OK: {len(cases)} cases validated")


def cmd_list(_: argparse.Namespace) -> None:
    for case in iter_cases():
        print(f"{case['id']:<22} {case['difficulty']:<7} {case['upstream_repo']:<28} {case['track']}")


def cmd_brief(args: argparse.Namespace) -> None:
    print(json.dumps(safe_brief(load_case(args.case_id)), indent=2, ensure_ascii=False))


def cmd_doctor(args: argparse.Namespace) -> None:
    case = load_case(args.case_id)
    missing: list[str] = []
    for binary in case["runtime"].get("required_bins", []):
        found = shutil.which(binary)
        print(f"{binary}: {found or 'MISSING'}")
        if not found:
            missing.append(binary)
    setup = case["validation"].get("setup", [])
    if setup:
        print("\nSetup commands (not run automatically):")
        for item in setup:
            print(f"  [{item['cwd']}] {' '.join(item['argv'])}")
    notes = case["runtime"].get("notes")
    if notes:
        print(f"\nNotes: {notes}")
    if missing:
        raise BenchError(f"missing required executables: {', '.join(missing)}")


def cmd_prepare(args: argparse.Namespace) -> None:
    case = load_case(args.case_id)
    dest = worktree(case)
    if dest.exists():
        if not args.recreate:
            raise BenchError(f"{dest} already exists; use --recreate to replace it")
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    run(["git", "init", str(dest)])
    remote = f"https://github.com/{case['upstream_repo']}.git"
    run(["git", "-C", str(dest), "remote", "add", "origin", remote])
    fetch = ["git", "-C", str(dest), "-c", "protocol.version=2", "fetch", "--filter=blob:none", "--no-tags"]
    if args.history_depth > 0:
        fetch.append(f"--depth={args.history_depth}")
    fetch.extend(["origin", case["base_sha"]])
    run(fetch)
    run(["git", "-C", str(dest), "checkout", "--detach", "FETCH_HEAD"])
    head = run(["git", "-C", str(dest), "rev-parse", "HEAD"], capture=True).stdout.strip()
    if head != case["base_sha"]:
        raise BenchError(f"prepared HEAD {head} does not match pinned base {case['base_sha']}")
    print(dest)


def assert_prepared(case: dict[str, Any]) -> Path:
    dest = worktree(case)
    if not (dest / ".git").exists():
        raise BenchError(f"case is not prepared: {dest}")
    return dest


def cmd_status(args: argparse.Namespace) -> None:
    case = load_case(args.case_id)
    dest = assert_prepared(case)
    head = run(["git", "-C", str(dest), "rev-parse", "HEAD"], capture=True).stdout.strip()
    status = run(["git", "-C", str(dest), "status", "--short"], capture=True).stdout.rstrip()
    print(f"case: {case['id']}")
    print(f"pinned_base: {case['base_sha']}")
    print(f"head: {head}")
    print("working_tree:")
    print(status or "  clean")


def command_cwd(dest: Path, relative: str) -> Path:
    target = (dest / relative).resolve()
    root = dest.resolve()
    if target != root and root not in target.parents:
        raise BenchError(f"validation cwd escapes checkout: {relative!r}")
    if not target.is_dir():
        raise BenchError(f"validation cwd does not exist: {target}")
    return target


def cmd_validate(args: argparse.Namespace) -> None:
    case = load_case(args.case_id)
    dest = assert_prepared(case)
    commands = case["validation"].get("tiers", {}).get(args.tier, [])
    if not commands:
        print(f"No fixed {args.tier!r} command is defined for {case['id']}.")
        guidance = case["validation"].get("guidance")
        if guidance:
            print(guidance)
        return
    for item in commands:
        run(item["argv"], cwd=command_cwd(dest, item["cwd"]))


def cmd_setup(args: argparse.Namespace) -> None:
    case = load_case(args.case_id)
    dest = assert_prepared(case)
    commands = case["validation"].get("setup", [])
    if not commands:
        print("No setup commands are defined for this case.")
        return
    if not args.i_understand_downloads:
        raise BenchError("setup may download/install large upstream dependencies; rerun with --i-understand-downloads")
    for item in commands:
        run(item["argv"], cwd=command_cwd(dest, item["cwd"]))


def cmd_capture(args: argparse.Namespace) -> None:
    case = load_case(args.case_id)
    dest = assert_prepared(case)
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    out_dir = RESULTS_DIR / case["id"] / stamp
    out_dir.mkdir(parents=True, exist_ok=False)
    diff = run(["git", "-C", str(dest), "diff", "--binary"], capture=True).stdout
    status = run(["git", "-C", str(dest), "status", "--short"], capture=True).stdout
    head = run(["git", "-C", str(dest), "rev-parse", "HEAD"], capture=True).stdout.strip()
    diff_path = out_dir / "candidate.diff"
    diff_path.write_text(diff, encoding="utf-8")
    record = {
        "case_id": case["id"],
        "upstream_repo": case["upstream_repo"],
        "pinned_base": case["base_sha"],
        "captured_head": head,
        "captured_at": now.isoformat(),
        "working_tree_status": status.splitlines(),
        "candidate_diff_sha256": hashlib.sha256(diff.encode("utf-8")).hexdigest(),
    }
    (out_dir / "run.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(out_dir)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("audit", help="validate all case files")
    p.set_defaults(func=cmd_audit)
    p = sub.add_parser("list", help="list benchmark cases")
    p.set_defaults(func=cmd_list)
    p = sub.add_parser("brief", help="print candidate-safe case metadata")
    p.add_argument("case_id")
    p.set_defaults(func=cmd_brief)
    p = sub.add_parser("doctor", help="check required local executables and show setup commands")
    p.add_argument("case_id")
    p.set_defaults(func=cmd_doctor)
    p = sub.add_parser("prepare", help="create a detached checkout at the pinned buggy base")
    p.add_argument("case_id")
    p.add_argument("--history-depth", type=int, default=200, help="ancestor history to fetch; 0 requests full reachable history")
    p.add_argument("--recreate", action="store_true")
    p.set_defaults(func=cmd_prepare)
    p = sub.add_parser("status", help="show pinned base, current HEAD, and worktree changes")
    p.add_argument("case_id")
    p.set_defaults(func=cmd_status)
    p = sub.add_parser("setup", help="run explicitly listed dependency setup commands")
    p.add_argument("case_id")
    p.add_argument("--i-understand-downloads", action="store_true")
    p.set_defaults(func=cmd_setup)
    p = sub.add_parser("validate", help="run a fixed validation tier without a shell")
    p.add_argument("case_id")
    p.add_argument("--tier", choices=["smoke", "focused", "full"], default="focused")
    p.set_defaults(func=cmd_validate)
    p = sub.add_parser("capture", help="capture candidate diff and reproducibility metadata locally")
    p.add_argument("case_id")
    p.set_defaults(func=cmd_capture)
    return parser


def main() -> int:
    try:
        args = build_parser().parse_args()
        args.func(args)
        return 0
    except (BenchError, subprocess.CalledProcessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
