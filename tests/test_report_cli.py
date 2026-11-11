import json
import sys
from datetime import date
from pathlib import Path

import pytest

from incident_pattern_miner.cli import main
from incident_pattern_miner.cluster import Theme
from incident_pattern_miner.ingest import Incident
from incident_pattern_miner.report import (add_generated_summaries, bucket_of, bucket_range,
                                           build_report, describe, to_html, to_markdown,
                                           trend_direction)

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
PATHS = [str(EXAMPLES / "postmortems"), str(EXAMPLES / "incidents.csv")]


def inc(number, day, severity="", services=()):
    return Incident(f"I{number}", f"Incident <{number}>", day, "text", severity, tuple(services))


@pytest.fixture()
def report():
    theme = Theme("certificate / expire", ("certificate", "expire"), (
        inc(1, date(2025, 11, 20), "SEV2", ["web"]), inc(2, date(2026, 2, 1), "SEV1", ["web", "api"]),
        inc(3, date(2026, 5, 2), "SEV2")))
    return build_report([theme], [inc(4, date(2026, 4, 1))])


def test_buckets():
    assert bucket_of(date(2026, 3, 31), "quarter") == "2026-Q1"
    assert bucket_of(date(2026, 4, 1), "quarter") == "2026-Q2"
    assert bucket_of(date(2026, 4, 1), "month") == "2026-04"
    assert bucket_range(date(2025, 11, 20), date(2026, 5, 2), "quarter") == ["2025-Q4", "2026-Q1", "2026-Q2"]
    assert bucket_range(date(2025, 12, 5), date(2026, 2, 1), "month") == ["2025-12", "2026-01", "2026-02"]
    assert bucket_range(date(2026, 2, 1), date(2026, 2, 9), "quarter") == ["2026-Q1"]


@pytest.mark.parametrize("counts, expected", [
    ([1, 0, 2, 3], "rising"), ([3, 1, 0, 1], "falling"), ([1, 1, 1], "steady"), ([2, 9, 2], "steady"),
    ([0, 0, 2], "new"), ([4], "n/a"), ([0, 1, 0, 2, 1], "rising"),
])
def test_trend_direction(counts, expected):
    assert trend_direction(counts) == expected


def test_build_report_and_describe(report):
    row = report.themes[0]
    assert report.buckets == ("2025-Q4", "2026-Q1", "2026-Q2") and report.total == 4
    assert row.counts == (1, 1, 1) and row.trend == "steady"
    assert describe(row.theme) == (
        "3 incidents between 2025-11-20 and 2026-05-02. Average gap between occurrences: 82 days. "
        "Severity: SEV1 x1, SEV2 x2. Services involved: web (2), api (1).")
    with pytest.raises(ValueError):
        build_report([], [])


def test_markdown_report(report):
    text = to_markdown(report)
    assert "4 incidents from 2025-11-20 to 2026-05-02. 3 of them (75%) fall into 1 recurring theme; 1 is a one-off." in text
    assert "| 1 | certificate / expire | 3 | 75% | 2025-11-20 | 2026-05-02 | steady |" in text
    assert "| certificate / expire | 1 | 1 | 1 |" in text
    assert "| (one-offs) | 0 | 0 | 1 |" in text
    assert text.index("2026-05-02 [SEV2] Incident <3>") < text.index("2025-11-20 [SEV2] Incident <1>")
    assert "## One-off incidents\n\n- 2026-04-01 Incident <4> (`I4`)" in text


def test_markdown_report_without_themes():
    text = to_markdown(build_report([], [inc(1, date(2026, 1, 1))]))
    assert "No group of similar incidents was found" in text


def test_html_report_escapes_and_is_self_contained(report):
    page = to_html(report)
    assert page.startswith("<!doctype html>") and page.rstrip().endswith("</html>")
    assert "Incident &lt;3&gt;" in page and "<3>" not in page
    assert "http" not in page  # no external assets


class FakeGenerator:
    def __init__(self, reply="They share an expired certificate."):
        self.reply, self.prompts = reply, []

    def generate(self, prompt):
        self.prompts.append(prompt)
        if self.reply is None:
            raise RuntimeError("offline")
        return self.reply


def test_generated_summaries_are_appended(report):
    fake = FakeGenerator()
    updated, warnings = add_generated_summaries(report, fake)
    assert warnings == []
    assert updated.themes[0].summary.endswith("\n\nThey share an expired certificate.")
    assert updated.themes[0].summary.startswith("3 incidents between")
    assert "Key terms: certificate, expire" in fake.prompts[0] and "- 2026-02-01 Incident <2>" in fake.prompts[0]


def test_generated_summary_failure_keeps_facts(report):
    updated, warnings = add_generated_summaries(report, FakeGenerator(reply=None))
    assert updated.themes[0].summary == report.themes[0].summary
    assert warnings == ["certificate / expire: generator failed (offline)"]


def test_cli_matches_committed_report(capsys):
    assert main(["analyze", *PATHS]) == 0
    assert capsys.readouterr().out == (EXAMPLES / "report.md").read_text("utf-8")


def test_cli_since_json_and_month_buckets(capsys):
    assert main(["analyze", *PATHS, "--since", "2026-01-01", "--format", "json", "--bucket", "month"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["buckets"] == ["2026-01", "2026-02", "2026-03"]
    assert data["total_incidents"] == 6
    assert all(i["date"] >= "2026-01-01" for t in data["themes"] for i in t["incidents"])
    assert data["themes"][0]["label"].startswith("certificate")


def test_cli_html_output_file_and_summary_command(tmp_path, capsys):
    out = tmp_path / "report.html"
    command = f'{sys.executable} -c "import sys; sys.stdin.read(); print(\'Generated paragraph.\')"'
    assert main(["analyze", *PATHS, "--format", "html", "-o", str(out), "--summary-command", command]) == 0
    page = out.read_text()
    assert "<h2>Recurring themes</h2>" in page and page.count("<p>Generated paragraph.</p>") == 4


def test_cli_errors(tmp_path, capsys):
    assert main(["analyze", str(tmp_path / "missing")]) == 2
    assert main(["analyze", *PATHS, "--since", "2030-01-01"]) == 1
    assert "no incidents found" in capsys.readouterr().err
    with pytest.raises(SystemExit):
        main(["analyze", *PATHS, "--threshold", "2"])
    with pytest.raises(SystemExit):
        main(["analyze", *PATHS, "--since", "soon"])
