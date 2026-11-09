"""Command-line entry point for individual Phase 2 checks."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from av1_monitor.checkers.factory import create_checker
from av1_monitor.registry import load_registry
from av1_monitor.runner import run_monitor
from av1_monitor.scan import scan_accommodation, write_reports


def valid_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("date must be YYYY-MM-DD") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="av1-monitor")
    parser.add_argument(
        "--registry", type=Path, default=Path("config/accommodations.toml")
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    check = subparsers.add_parser("check", help="run one non-binding availability check")
    check.add_argument("--accommodation", required=True)
    check.add_argument("--date", type=valid_date, required=True)
    check.add_argument("--party-size", type=int, default=3)
    check.add_argument("--evidence-dir", type=Path)

    scan = subparsers.add_parser("scan", help="scan every night in a date range")
    selection = scan.add_mutually_exclusive_group(required=True)
    selection.add_argument("--accommodation", action="append")
    selection.add_argument("--all", action="store_true")
    scan.add_argument("--start-date", type=valid_date)
    scan.add_argument("--end-date", type=valid_date)
    scan.add_argument("--party-size", type=int)
    scan.add_argument("--host-delay", type=float)
    scan.add_argument("--evidence-dir", type=Path)
    scan.add_argument("--output-dir", type=Path, default=Path("artifacts/latest"))

    run = subparsers.add_parser(
        "run", help="scan, reduce transitions, notify, and persist state"
    )
    run_selection = run.add_mutually_exclusive_group(required=True)
    run_selection.add_argument("--accommodation", action="append")
    run_selection.add_argument("--all", action="store_true")
    run.add_argument("--start-date", type=valid_date)
    run.add_argument("--end-date", type=valid_date)
    run.add_argument("--party-size", type=int)
    run.add_argument("--host-delay", type=float)
    run.add_argument("--evidence-dir", type=Path)
    run.add_argument("--output-dir", type=Path, default=Path("artifacts/latest"))
    run.add_argument("--state-in", type=Path)
    run.add_argument(
        "--state-out", type=Path, default=Path("artifacts/latest/monitor-state.json")
    )
    run.add_argument("--github-issues", action="store_true")
    run.add_argument("--dry-run", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    registry = load_registry(args.registry)
    party_size = args.party_size or registry.monitor.party_size
    if party_size < 1:
        raise SystemExit("--party-size must be at least 1")
    if args.command == "check":
        try:
            accommodation = registry.get(args.accommodation)
        except KeyError as exc:
            raise SystemExit(f"unknown accommodation: {args.accommodation}") from exc
        checker = create_checker(accommodation)
        result = checker.check(args.date, party_size, args.evidence_dir)
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        return

    start_date = args.start_date or registry.monitor.start_date
    end_date = args.end_date or registry.monitor.end_date
    delay = (
        args.host_delay
        if args.host_delay is not None
        else registry.monitor.host_delay_seconds
    )
    if args.all:
        accommodations = registry.accommodations
    else:
        try:
            accommodations = tuple(registry.get(item) for item in args.accommodation)
        except KeyError as exc:
            raise SystemExit(f"unknown accommodation: {exc.args[0]}") from exc
    if args.command == "run":
        outcome = run_monitor(
            accommodations=accommodations,
            start_date=start_date,
            end_date=end_date,
            party_size=party_size,
            host_delay_seconds=delay,
            output_dir=args.output_dir,
            state_input=args.state_in,
            state_output=args.state_out,
            evidence_dir=args.evidence_dir,
            github_issues=args.github_issues,
            dry_run=args.dry_run,
        )
        print(json.dumps(outcome.to_dict(), indent=2, ensure_ascii=False))
        return

    scans = tuple(
        scan_accommodation(
            accommodation,
            start_date,
            end_date,
            party_size,
            delay,
            args.evidence_dir,
        )
        for accommodation in accommodations
    )
    write_reports(scans, args.output_dir)
    print(json.dumps([scan.to_dict() for scan in scans], indent=2, ensure_ascii=False))

