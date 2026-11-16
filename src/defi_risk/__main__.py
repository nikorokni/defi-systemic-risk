"""Command-line entry point. Run commands from the repository root."""

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/study.json"))
    parser.add_argument("--sources", type=Path, default=Path("configs/sources.json"))
    parser.add_argument("--raw", type=Path, default=Path("data/raw"))
    parser.add_argument("--processed", type=Path, default=Path("data/processed"))
    commands = parser.add_subparsers(dest="action", required=True)
    commands.add_parser("fetch")
    commands.add_parser("prepare")
    run = commands.add_parser("evaluate")
    run.add_argument("--hours", type=int, choices=[6, 24, 168], default=24)
    run.add_argument("--scaled", action="store_true")
    run.add_argument("--out", type=Path, default=Path("results"))
    report = commands.add_parser("report")
    report.add_argument("--out", type=Path, default=Path("results"))
    report.add_argument("--figures", type=Path, default=Path("figures"))
    args = parser.parse_args()
    study = json.loads(args.config.read_text())
    sources = json.loads(args.sources.read_text())
    if args.action == "fetch":
        from .data import fetch
        fetch(sources, args.raw)
    elif args.action == "prepare":
        from .data import prepare
        prepare(sources, args.raw, args.processed, study)
    elif args.action == "evaluate":
        from .run import evaluate
        if args.scaled and args.hours != 24:
            parser.error("--scaled is defined for the 24-hour sensitivity arm")
        folders = {6: "six_hour", 24: "primary", 168: "seven_day"}
        target = "borrowing_scaled" if args.scaled else folders[args.hours]
        evaluate(args.processed, args.out / target, study, args.hours, args.scaled)
    elif args.action == "report":
        from .report import run_report
        run_report(args.out, args.processed, args.figures, study)


if __name__ == "__main__":
    main()
