from datetime import date

import pytest

from incident_pattern_miner.ingest import InputError, load_paths, parse_csv, parse_date, parse_markdown

FRONT = """---
title: "Gateway certificate expired"
date: 2026-01-12
severity: sev1
services: [api-gateway, web]
id: INC-7
---

## Summary

TLS handshakes failed.

## Timeline

- 10:00 everything is noise here

## Root cause

Nobody renewed the certificate.
"""

BOLD = """# Postmortem: Bad config push

- **Date:** 2026/02/03 14:00 UTC
- **Severity:** SEV2
**Services:** checkout; payments

## What happened

A config push broke checkout.
"""


def test_parse_date_variants():
    assert parse_date("2026-01-12") == date(2026, 1, 12)
    assert parse_date("started 2026/1/2 at 10:00") == date(2026, 1, 2)
    assert parse_date("2026-01-12T10:00:00Z") == date(2026, 1, 12)
    assert parse_date("2026-13-40") is None
    assert parse_date("yesterday") is None


def test_markdown_front_matter():
    incident = parse_markdown(FRONT, "postmortems/whatever.md")
    assert incident.id == "INC-7"
    assert incident.title == "Gateway certificate expired"
    assert incident.date == date(2026, 1, 12)
    assert incident.severity == "SEV1"
    assert incident.services == ("api-gateway", "web")
    assert "Nobody renewed" in incident.text and "TLS handshakes" in incident.text
    assert "noise" not in incident.text  # the timeline section is not used for clustering


def test_markdown_bold_metadata_and_title_prefix():
    incident = parse_markdown(BOLD, "pm/2026-02-03-config.md")
    assert incident.title == "Bad config push"
    assert incident.date == date(2026, 2, 3)
    assert incident.severity == "SEV2"
    assert incident.services == ("checkout", "payments")
    assert incident.id == "2026-02-03-config"


def test_markdown_date_from_file_name_and_whole_body_fallback():
    incident = parse_markdown("# Disk full\n\nThe log volume filled up.\n", "2025-12-01-disk-full.md")
    assert incident.date == date(2025, 12, 1)
    assert "log volume filled" in incident.text


def test_markdown_without_date_is_none():
    assert parse_markdown("# Mystery\n\nNo date anywhere.\n", "notes.md") is None


def test_csv_rows_and_skips():
    text = ("Key,Summary,Created,Priority,Component,Description\n"
            "OPS-1,Cert expired,2026-01-05T10:00:00Z,p2,web,The cert expired\n"
            ",No date here,,,,\n"
            ",Second,2026-02-01,,a;b,\n")
    incidents, skipped = parse_csv(text, "export.csv")
    assert [i.id for i in incidents] == ["OPS-1", "export:4"]
    assert incidents[0].severity == "P2" and incidents[0].services == ("web",)
    assert incidents[0].text == "Cert expired The cert expired"
    assert incidents[1].services == ("a", "b")
    assert skipped == ["export.csv:3: no title or no date"]


def test_load_paths_mixes_sources_and_sorts(tmp_path):
    (tmp_path / "pm").mkdir()
    (tmp_path / "pm" / "2026-03-01-b.md").write_text("# B\n\nbody\n")
    (tmp_path / "pm" / "README.md").write_text("# About this folder\n")
    (tmp_path / "pm" / "undated.md").write_text("# Undated\n\nbody\n")
    csv_file = tmp_path / "old.csv"
    csv_file.write_text("title,date\nA,2025-01-01\n")
    incidents, skipped = load_paths([str(tmp_path / "pm"), str(csv_file)])
    assert [i.title for i in incidents] == ["A", "B"]
    assert len(skipped) == 1 and "undated.md: no date found" in skipped[0]


def test_load_paths_errors(tmp_path):
    with pytest.raises(InputError, match="no such file"):
        load_paths([str(tmp_path / "missing")])
    other = tmp_path / "notes.txt"
    other.write_text("x")
    with pytest.raises(InputError, match="unsupported file type"):
        load_paths([str(other)])
