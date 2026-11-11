"""Command-line interface."""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from . import __version__
from .cluster import find_themes
from .ingest import InputError, load_paths, parse_date
from .report import (CommandGenerator, add_generated_summaries, build_report, to_html, to_json,
                     to_markdown)

_RENDERERS = {"markdown": to_markdown, "html": to_html, "json": to_json}


def _date(value: str) -> date:
    parsed = parse_date(value)
    if parsed is None:
        raise argparse.ArgumentTypeError(f"not a date (expected YYYY-MM-DD): {value}")
    return parsed


def _threshold(value: str) -> float:
    number = float(value)
    if not 0 < number <= 1:
        raise argparse.ArgumentTypeError("threshold must be greater than 0 and at most 1")
    return number


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="incident-pattern-miner",
        description="Group past incidents into recurring themes and report how often each "
                    "theme comes back.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    analyze = commands.add_parser("analyze", help="cluster incidents and write a report")
    analyze.add_argument("paths", nargs="+", metavar="PATH",
                         help="directories of Markdown postmortems, .md files or .csv exports")
    analyze.add_argument("--since", type=_date, metavar="YYYY-MM-DD",
                         help="ignore incidents before this date")
    analyze.add_argument("--until", type=_date, metavar="YYYY-MM-DD",
                         help="ignore incidents after this date")
    analyze.add_argument("--format", choices=sorted(_RENDERERS), default="markdown")
    analyze.add_argument("--bucket", choices=("quarter", "month"), default="quarter",
                         help="period used for the trend table (default: quarter)")
    analyze.add_argument("--threshold", type=_threshold, default=0.15, metavar="0-1",
                         help="minimum average similarity for incidents to share a theme "
                              "(default: 0.15; higher gives more, tighter themes)")
    analyze.add_argument("--min-size", type=int, default=2, metavar="N",
                         help="smallest group reported as a theme (default: 2)")
    analyze.add_argument("--summary-command", metavar="COMMAND",
                         help="optional: add a generated paragraph per theme by piping a prompt "
                              "to COMMAND (reads stdin, writes stdout). Off by default.")
    analyze.add_argument("-o", "--output", metavar="FILE", help="write to FILE instead of stdout")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        incidents, skipped = load_paths(args.paths)
    except InputError as exc:
        print(f"incident-pattern-miner: error: {exc}", file=sys.stderr)
        return 2
    for note in skipped:
        print(f"incident-pattern-miner: skipped {note}", file=sys.stderr)
    incidents = [i for i in incidents
                 if (not args.since or i.date >= args.since) and (not args.until or i.date <= args.until)]
    if not incidents:
        print("incident-pattern-miner: no incidents found in the given paths and date range",
              file=sys.stderr)
        return 1

    themes, one_offs = find_themes(incidents, args.threshold, max(args.min_size, 2))
    report = build_report(themes, one_offs, args.bucket)
    if args.summary_command:
        report, warnings = add_generated_summaries(report, CommandGenerator(args.summary_command))
        for warning in warnings:
            print(f"incident-pattern-miner: warning: {warning}", file=sys.stderr)
    output = _RENDERERS[args.format](report)
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"wrote {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
