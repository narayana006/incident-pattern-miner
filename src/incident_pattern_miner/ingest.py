"""Load incidents from Markdown postmortems and CSV exports."""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path


class InputError(ValueError):
    """An input path is missing or not in a supported shape."""


@dataclass(frozen=True)
class Incident:
    id: str
    title: str
    date: date
    text: str  # what the clustering reads: the title plus the descriptive sections
    severity: str = ""
    services: tuple[str, ...] = field(default_factory=tuple)
    source: str = ""


def parse_date(value: str) -> date | None:
    """Find a date in a string: 2026-01-12, 2026/01/12 or an ISO timestamp."""
    match = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", value or "")
    if not match:
        return None
    try:
        return datetime(int(match.group(1)), int(match.group(2)), int(match.group(3))).date()
    except ValueError:
        return None


def _split_list(value: str) -> tuple[str, ...]:
    return tuple(part.strip().strip("'\"") for part in re.split(r"[,;]", value.strip("[] "))
                 if part.strip().strip("'\""))


# --------------------------------------------------------------------------
# Markdown
# --------------------------------------------------------------------------

_FRONT_MATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)
# "Date: ...", "**Date:** ...", "- **Date**: ..." near the top of the document.
_META_LINE = re.compile(r"^\s*(?:[-*]\s+)?\**([A-Za-z][A-Za-z ]{1,30}?)\**\s*:\s*\**\s*(.+?)\s*$")
_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_TITLE_PREFIX = re.compile(r"^(?:post[- ]?mortem|incident(?: review| report)?|pir|rca)\s*[:\-]\s*", re.I)
# Sections that describe what failed. The timeline and action items are left
# out because they are full of words every incident shares.
_DESCRIPTIVE = re.compile(
    r"summary|what happened|root cause|cause|trigger|fault|leadup|contributing|what went wrong"
    r"|impact|description|overview", re.I)
_DATE_KEYS = ("date", "incident date", "started", "start", "occurred", "created")
_SERVICE_KEYS = ("services", "service", "components", "component", "systems", "system")


def parse_markdown(text: str, source: str = "") -> Incident | None:
    """Parse one postmortem. Returns None when no date can be found."""
    meta: dict[str, str] = {}
    front = _FRONT_MATTER.match(text)
    if front:
        for line in front.group(1).splitlines():
            key, sep, value = line.partition(":")
            if sep and value.strip():
                meta[key.strip().lower()] = value.strip().strip("'\"")
        text = text[front.end():]

    title = meta.get("title", "")
    sections: list[tuple[str, list[str]]] = [("", [])]
    for number, line in enumerate(text.splitlines()):
        heading = _HEADING.match(line)
        if heading:
            if len(heading.group(1)) == 1 and not title:
                title = heading.group(2)
            else:
                sections.append((heading.group(2), []))
            continue
        if number < 40 and len(sections) == 1:
            found = _META_LINE.match(line)
            if found:
                meta.setdefault(found.group(1).strip().lower(), found.group(2))
                continue
        sections[-1][1].append(line)

    stem = Path(source).stem if source else ""
    title = _TITLE_PREFIX.sub("", title).strip() or stem.replace("-", " ")
    when = next((parsed for key in _DATE_KEYS if (parsed := parse_date(meta.get(key, "")))), None)
    when = when or parse_date(stem)
    if when is None:
        return None

    chosen = [" ".join(body) for name, body in sections if _DESCRIPTIVE.search(name)]
    if not any(part.strip() for part in chosen):
        chosen = [" ".join(body) for _, body in sections]
    services = next((_split_list(meta[key]) for key in _SERVICE_KEYS if meta.get(key)), ())
    return Incident(id=meta.get("id") or stem or title, title=title, date=when,
                    text=" ".join([title, *chosen]), severity=_severity(meta), services=services,
                    source=source)


def _severity(meta: dict[str, str]) -> str:
    value = meta.get("severity") or meta.get("sev") or meta.get("priority") or ""
    return value.strip().upper()


# --------------------------------------------------------------------------
# CSV
# --------------------------------------------------------------------------

def _pick(row: dict[str, str], *names: str) -> str:
    for name in names:
        if (row.get(name) or "").strip():
            return row[name].strip()
    return ""


def parse_csv(text: str, source: str = "") -> tuple[list[Incident], list[str]]:
    """Parse a CSV export. Returns the incidents and a list of skipped-row notes.

    Needs a title (`title`, `summary` or `name`) and a date (`date`,
    `created`, `created_at`, `started_at` or `opened`). Optional: `id`/`key`/`issue_key`,
    `severity`/`priority`, `service`/`services`, and free text in
    `description`, `root_cause` or `details`.
    """
    reader = csv.DictReader(io.StringIO(text))
    incidents, skipped = [], []
    for number, raw in enumerate(reader, start=2):
        row = {(key or "").strip().lower().replace(" ", "_"): value or "" for key, value in raw.items()}
        title = _pick(row, "title", "summary", "name")
        when = parse_date(_pick(row, "date", "created", "created_at", "started_at", "opened"))
        if not title or when is None:
            skipped.append(f"{source}:{number}: no title or no date")
            continue
        body = " ".join(row.get(name, "") for name in ("description", "root_cause", "details"))
        incidents.append(Incident(
            id=_pick(row, "id", "key", "issue_key", "incident_id") or f"{Path(source).stem}:{number}",
            title=title, date=when, text=f"{title} {body}".strip(),
            severity=_pick(row, "severity", "priority").upper(),
            services=_split_list(_pick(row, "services", "service", "component")), source=source))
    return incidents, skipped


# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------

def load_paths(paths: list[str]) -> tuple[list[Incident], list[str]]:
    """Load every .md/.markdown and .csv file under the given paths.

    Returns incidents sorted by date and a list of notes about skipped inputs.
    """
    files: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            files.extend(sorted(p for p in path.rglob("*")
                                if p.suffix.lower() in (".md", ".markdown", ".csv")
                                and p.name.lower() != "readme.md"))
        elif path.is_file():
            files.append(path)
        else:
            raise InputError(f"no such file or directory: {raw}")

    incidents: list[Incident] = []
    skipped: list[str] = []
    for file in files:
        try:
            text = file.read_text("utf-8-sig")
        except (OSError, UnicodeDecodeError) as exc:
            raise InputError(f"cannot read {file}: {exc}") from None
        if file.suffix.lower() == ".csv":
            found, notes = parse_csv(text, str(file))
            incidents.extend(found)
            skipped.extend(notes)
        elif file.suffix.lower() in (".md", ".markdown"):
            incident = parse_markdown(text, str(file))
            if incident:
                incidents.append(incident)
            else:
                skipped.append(f"{file}: no date found (add a 'Date:' line or a dated file name)")
        else:
            raise InputError(f"unsupported file type: {file} (expected .md or .csv)")
    incidents.sort(key=lambda incident: (incident.date, incident.id))
    return incidents, skipped
