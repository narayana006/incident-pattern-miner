"""Trend calculation and report rendering (Markdown, HTML, JSON)."""

from __future__ import annotations

import html
import json
import shlex
import subprocess
from collections import Counter
from dataclasses import dataclass
from datetime import date
from typing import Protocol

from .cluster import Theme
from .ingest import Incident


def bucket_of(day: date, size: str) -> str:
    """Name of the quarter ("2026-Q1") or month ("2026-01") a date falls in."""
    return f"{day.year}-Q{(day.month - 1) // 3 + 1}" if size == "quarter" else f"{day.year}-{day.month:02d}"


def bucket_range(first: date, last: date, size: str) -> list[str]:
    """Every bucket from `first` to `last`, including empty ones in between."""
    step = 3 if size == "quarter" else 1
    month_index = first.year * 12 + (first.month - 1) // step * step
    end_index = last.year * 12 + last.month - 1
    buckets = []
    while month_index <= end_index:
        buckets.append(bucket_of(date(month_index // 12, month_index % 12 + 1, 1), size))
        month_index += step
    return buckets


def trend_direction(counts: list[int]) -> str:
    """Compare the later half of the period with the earlier half.

    "new" means every incident is in the latest bucket. With an odd number of
    buckets the middle one is ignored.
    """
    if len(counts) < 2:
        return "n/a"
    if sum(counts[:-1]) == 0 and counts[-1] > 0:
        return "new"
    half = len(counts) // 2
    earlier, later = sum(counts[:half]), sum(counts[-half:])
    if later > earlier:
        return "rising"
    return "falling" if later < earlier else "steady"


@dataclass(frozen=True)
class ThemeReport:
    theme: Theme
    counts: tuple[int, ...]  # incidents per bucket, aligned with Report.buckets
    trend: str
    summary: str

    @property
    def size(self) -> int:
        return len(self.theme.incidents)


@dataclass(frozen=True)
class Report:
    buckets: tuple[str, ...]
    bucket_size: str
    total: int
    themes: tuple[ThemeReport, ...]
    one_offs: tuple[Incident, ...]
    first: date
    last: date


def describe(theme: Theme) -> str:
    """One deterministic paragraph of facts about a theme."""
    incidents = theme.incidents
    parts = [f"{len(incidents)} incidents between {incidents[0].date} and {incidents[-1].date}."]
    gaps = [(b.date - a.date).days for a, b in zip(incidents, incidents[1:])]
    if gaps:
        parts.append(f"Average gap between occurrences: {round(sum(gaps) / len(gaps))} days.")
    severities = Counter(i.severity for i in incidents if i.severity)
    if severities:
        parts.append("Severity: " + ", ".join(f"{name} x{count}" for name, count in
                                              sorted(severities.items())) + ".")
    services = Counter(service for i in incidents for service in i.services)
    if services:
        parts.append("Services involved: " + ", ".join(
            f"{name} ({count})" for name, count in
            sorted(services.items(), key=lambda item: (-item[1], item[0]))[:5]) + ".")
    return " ".join(parts)


def build_report(themes: list[Theme], one_offs: list[Incident], bucket_size: str = "quarter") -> Report:
    everything = [i for theme in themes for i in theme.incidents] + list(one_offs)
    if not everything:
        raise ValueError("no incidents to report on")
    first, last = min(i.date for i in everything), max(i.date for i in everything)
    buckets = bucket_range(first, last, bucket_size)
    rows = []
    for theme in themes:
        tally = Counter(bucket_of(i.date, bucket_size) for i in theme.incidents)
        counts = tuple(tally.get(bucket, 0) for bucket in buckets)
        rows.append(ThemeReport(theme, counts, trend_direction(list(counts)), describe(theme)))
    return Report(tuple(buckets), bucket_size, len(everything), tuple(rows), tuple(one_offs), first, last)


# --------------------------------------------------------------------------
# Optional generated summaries
# --------------------------------------------------------------------------

class TextGenerator(Protocol):
    def generate(self, prompt: str) -> str:
        """Return generated text for the prompt."""


class CommandGenerator:
    """Send the prompt to a command's stdin and use its stdout as the result."""

    def __init__(self, command: str, timeout: float = 120.0):
        self.argv = shlex.split(command)
        if not self.argv:
            raise ValueError("summary command is empty")
        self.timeout = timeout

    def generate(self, prompt: str) -> str:
        return subprocess.run(self.argv, input=prompt, capture_output=True, text=True,
                              timeout=self.timeout, check=True).stdout


PROMPT = """These incidents were grouped together as one recurring failure mode.
In two or three sentences, say what they have in common and what kind of fix would stop the
recurrence. Use only the information below.

Key terms: {terms}
{incidents}
"""


def add_generated_summaries(report: Report, generator: TextGenerator) -> tuple[Report, list[str]]:
    """Append a generated paragraph to each theme's summary.

    The factual summary is always kept; a failing generator only produces a warning.
    """
    rows, warnings = [], []
    for row in report.themes:
        listing = "\n".join(f"- {i.date} {i.title}" for i in row.theme.incidents)
        try:
            extra = generator.generate(PROMPT.format(terms=", ".join(row.theme.terms),
                                                     incidents=listing)).strip()
        except Exception as exc:  # keep the report usable whatever the generator does
            warnings.append(f"{row.theme.label}: generator failed ({exc})")
            extra = ""
        summary = f"{row.summary}\n\n{extra}" if extra else row.summary
        rows.append(ThemeReport(row.theme, row.counts, row.trend, summary))
    return Report(report.buckets, report.bucket_size, report.total, tuple(rows), report.one_offs,
                  report.first, report.last), warnings


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------

def _share(part: int, whole: int) -> str:
    return f"{round(100 * part / whole)}%"


def _one_offs(report: Report) -> str:
    count = len(report.one_offs)
    return "1 is a one-off" if count == 1 else f"{count} are one-offs"


def _incident_line(incident: Incident) -> str:
    severity = f" [{incident.severity}]" if incident.severity else ""
    return f"{incident.date}{severity} {incident.title} (`{incident.id}`)"


def to_markdown(report: Report) -> str:
    grouped = sum(row.size for row in report.themes)
    lines = [
        "# Incident pattern report", "",
        f"{report.total} incidents from {report.first} to {report.last}. "
        f"{grouped} of them ({_share(grouped, report.total)}) fall into {len(report.themes)} "
        f"recurring theme{'' if len(report.themes) == 1 else 's'}; {_one_offs(report)}.", "",
        "## Recurring themes", "",
    ]
    if report.themes:
        lines += ["| # | Theme | Incidents | Share | First seen | Last seen | Trend |",
                  "| --- | --- | --- | --- | --- | --- | --- |"]
        for number, row in enumerate(report.themes, 1):
            incidents = row.theme.incidents
            lines.append(f"| {number} | {row.theme.label} | {row.size} | {_share(row.size, report.total)} "
                         f"| {incidents[0].date} | {incidents[-1].date} | {row.trend} |")
        lines += ["", f"## Incidents per {report.bucket_size}", "",
                  "| Theme | " + " | ".join(report.buckets) + " |",
                  "| --- |" + " ---: |" * len(report.buckets)]
        for row in report.themes:
            lines.append(f"| {row.theme.label} | " + " | ".join(str(c) for c in row.counts) + " |")
        if report.one_offs:
            tally = Counter(bucket_of(i.date, report.bucket_size) for i in report.one_offs)
            lines.append("| (one-offs) | " + " | ".join(str(tally.get(b, 0)) for b in report.buckets) + " |")
        lines += ["", "## Theme details"]
        for number, row in enumerate(report.themes, 1):
            lines += ["", f"### {number}. {row.theme.label}", "", row.summary, "",
                      f"Key terms: {', '.join(row.theme.terms)}", ""]
            lines += [f"- {_incident_line(i)}" for i in reversed(row.theme.incidents)]
    else:
        lines.append("No group of similar incidents was found. Try a lower `--threshold`.")
    if report.one_offs:
        lines += ["", "## One-off incidents", ""]
        lines += [f"- {_incident_line(i)}" for i in report.one_offs]
    return "\n".join(lines) + "\n"


def to_json(report: Report) -> str:
    def incident(i: Incident) -> dict:
        return {"id": i.id, "title": i.title, "date": i.date.isoformat(), "severity": i.severity,
                "services": list(i.services), "source": i.source}

    return json.dumps({
        "period": {"first": report.first.isoformat(), "last": report.last.isoformat()},
        "bucket_size": report.bucket_size,
        "buckets": list(report.buckets),
        "total_incidents": report.total,
        "themes": [{"label": row.theme.label, "terms": list(row.theme.terms), "size": row.size,
                    "trend": row.trend, "counts": list(row.counts), "summary": row.summary,
                    "incidents": [incident(i) for i in row.theme.incidents]} for row in report.themes],
        "one_offs": [incident(i) for i in report.one_offs],
    }, indent=2) + "\n"


_CSS = """
body{font:15px/1.5 system-ui,sans-serif;max-width:60rem;margin:2rem auto;padding:0 1rem;color:#1d2433}
table{border-collapse:collapse;width:100%;margin:1rem 0}
th,td{border-bottom:1px solid #d8dde6;padding:.35rem .6rem;text-align:left;vertical-align:top}
td.n,th.n{text-align:right}
.bar{display:inline-block;height:.7rem;background:#3b6fd4;border-radius:2px;vertical-align:middle}
.cell{background:#3b6fd4;color:#fff;border-radius:3px;padding:0 .4rem}
.muted{color:#5c667a}
"""


def to_html(report: Report) -> str:
    """A self-contained HTML page with the same content as the Markdown report."""
    e = html.escape
    grouped = sum(row.size for row in report.themes)
    largest = max((row.size for row in report.themes), default=1)
    out = ["<!doctype html>", '<html lang="en"><head><meta charset="utf-8">',
           "<title>Incident pattern report</title>", f"<style>{_CSS}</style></head><body>",
           "<h1>Incident pattern report</h1>",
           f"<p>{report.total} incidents from {report.first} to {report.last}. {grouped} of them "
           f"({_share(grouped, report.total)}) fall into {len(report.themes)} recurring "
           f"theme{'' if len(report.themes) == 1 else 's'}; {_one_offs(report)}.</p>"]
    if report.themes:
        out.append('<h2>Recurring themes</h2><table><tr><th>Theme</th><th class="n">Incidents</th>'
                   "<th></th><th>First seen</th><th>Last seen</th><th>Trend</th></tr>")
        for row in report.themes:
            incidents = row.theme.incidents
            out.append(f'<tr><td>{e(row.theme.label)}</td><td class="n">{row.size}</td>'
                       f'<td><span class="bar" style="width:{round(10 * row.size / largest, 1)}rem">'
                       f"</span></td><td>{incidents[0].date}</td><td>{incidents[-1].date}</td>"
                       f"<td>{row.trend}</td></tr>")
        out.append(f"</table><h2>Incidents per {report.bucket_size}</h2><table><tr><th>Theme</th>"
                   + "".join(f'<th class="n">{b}</th>' for b in report.buckets) + "</tr>")
        for row in report.themes:
            cells = "".join(f'<td class="n">{f"<span class=cell>{c}</span>" if c else "<span class=muted>0</span>"}</td>'
                            for c in row.counts)
            out.append(f"<tr><td>{e(row.theme.label)}</td>{cells}</tr>")
        out.append("</table><h2>Theme details</h2>")
        for number, row in enumerate(report.themes, 1):
            out.append(f"<h3>{number}. {e(row.theme.label)}</h3>")
            out += [f"<p>{e(paragraph)}</p>" for paragraph in row.summary.split("\n\n")]
            out.append(f'<p class="muted">Key terms: {e(", ".join(row.theme.terms))}</p><ul>')
            out += [f"<li>{e(_incident_line(i).replace('`', ''))}</li>" for i in reversed(row.theme.incidents)]
            out.append("</ul>")
    else:
        out.append("<p>No group of similar incidents was found.</p>")
    if report.one_offs:
        out.append("<h2>One-off incidents</h2><ul>")
        out += [f"<li>{e(_incident_line(i).replace('`', ''))}</li>" for i in report.one_offs]
        out.append("</ul>")
    out.append("</body></html>")
    return "\n".join(out) + "\n"
