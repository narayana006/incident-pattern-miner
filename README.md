# incident-pattern-miner

Group past incidents into recurring themes, so you can see which failure modes keep coming back and whether each one is getting more or less frequent.

**Status:** first working version (v0.1.0). Working today: import from Markdown postmortems and CSV exports, clustering into themes, a factual summary and trend per theme, and reports in Markdown, HTML or JSON. Clustering uses TF-IDF text similarity computed locally, not neural embeddings, and the per-theme summary is computed facts, not generated prose (both can be plugged in, see below). Jira and PagerDuty imports are not built; export to CSV for now.

## Why

Each postmortem is reviewed on its own, so "the certificate expired again" is only noticed by whoever happens to remember the last time. Reading a year of incidents side by side is the fix, and it is tedious enough that it rarely happens. This tool does the side-by-side reading.

## Install

Requires Python 3.10 or newer. No runtime dependencies.

```bash
pip install git+https://github.com/narayana006/incident-pattern-miner
```

## Quick start

The repository ships 16 short fictional postmortems and a CSV with 4 more incidents.

```bash
git clone https://github.com/narayana006/incident-pattern-miner
cd incident-pattern-miner
incident-pattern-miner analyze examples/postmortems examples/incidents.csv
```

Output (themes 2 to 4 are cut here; the full report is [examples/report.md](examples/report.md)):

```markdown
# Incident pattern report

20 incidents from 2025-02-11 to 2026-03-14. 17 of them (85%) fall into 4 recurring themes; 3 are one-offs.

## Recurring themes

| # | Theme | Incidents | Share | First seen | Last seen | Trend |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | certificate / expire / renew | 6 | 30% | 2025-02-11 | 2026-03-09 | rising |
| 2 | configuration / push / staged | 5 | 25% | 2025-03-18 | 2026-02-12 | rising |
| 3 | connection / database / pool | 4 | 20% | 2025-04-29 | 2026-03-14 | rising |
| 4 | dns / lookup | 2 | 10% | 2025-05-13 | 2025-12-02 | steady |

## Incidents per quarter

| Theme | 2025-Q1 | 2025-Q2 | 2025-Q3 | 2025-Q4 | 2026-Q1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| certificate / expire / renew | 1 | 1 | 1 | 1 | 2 |
| configuration / push / staged | 1 | 0 | 2 | 1 | 1 |
| connection / database / pool | 0 | 1 | 1 | 1 | 1 |
| dns / lookup | 0 | 1 | 0 | 1 | 0 |
| (one-offs) | 0 | 0 | 1 | 0 | 2 |

## Theme details

### 1. certificate / expire / renew

6 incidents between 2025-02-11 and 2026-03-09. Average gap between occurrences: 78 days. Severity: SEV1 x1, SEV2 x2, SEV3 x2, SEV4 x1. Services involved: api-gateway (1), billing (1), cdn (1), notifications (1), partner-integrations (1).

Key terms: certificate, expire, renew, reminder, year, failed

- 2026-03-09 [SEV3] Partner API client certificate expired (`2026-03-09-partner-api-cert-expired`)
- 2026-01-27 [SEV2] CDN certificate renewal failed and certificate expired (`2026-01-27-cdn-cert-renewal-failed`)
- 2025-10-20 [SEV3] Outbound email stopped: SMTP relay certificate expired (`2025-10-20-smtp-cert-expired`)
- 2025-08-19 [SEV4] Status page certificate expired (`OPS-1412`)
- 2025-06-03 [SEV2] Internal CA intermediate certificate expiry broke service mesh (`2025-06-03-internal-ca-cert-expiry`)
- 2025-02-11 [SEV1] API gateway certificate expired (`2025-02-11-api-gateway-cert-expired`)

[...]

## One-off incidents

- 2025-08-07 [SEV3] Search index corrupted during reindex (`2025-08-07-search-index-corruption`)
- 2026-01-08 [SEV2] Third-party payment provider outage (`2026-01-08-payment-provider-outage`)
- 2026-02-03 [SEV4] Office VPN concentrator failed over (`OPS-1650`)
```

## Usage

```
incident-pattern-miner analyze PATH [PATH ...] [options]
```

Each `PATH` is a directory (searched recursively for `.md` and `.csv`; `README.md` is ignored), a Markdown file or a CSV file.

| Option | Meaning |
| --- | --- |
| `--since YYYY-MM-DD`, `--until YYYY-MM-DD` | Only analyse incidents in this date range. |
| `--format markdown\|html\|json` | Report format (default `markdown`). The HTML page is self-contained. |
| `--bucket quarter\|month` | Period for the trend table (default `quarter`). |
| `--threshold 0-1` | Minimum average similarity for incidents to share a theme (default `0.15`). Raise it for fewer, tighter themes; lower it if obviously related incidents are left as one-offs. |
| `--min-size N` | Smallest group reported as a theme (default `2`). |
| `--summary-command COMMAND` | Optional generated paragraph per theme; see below. |
| `-o FILE` | Write the report to a file. |

For example, a quarterly HTML report:

```bash
incident-pattern-miner analyze ./postmortems --since 2026-01-01 --format html -o q1-report.html
```

Exit status is 0 on success, 1 when no incidents match, 2 on a bad path. Files that are skipped (no date) are listed on stderr.

### Input formats

**Markdown postmortems.** One incident per file. The title is the front-matter `title` or the first `#` heading (a leading "Postmortem:" is dropped). The date comes from front matter, from a `Date:` / `**Date:**` line near the top, or from a file name such as `2026-01-27-cdn-cert.md`. `Severity` and `Services` are read the same way when present. For clustering, the tool reads the title plus the sections that describe the failure (summary, what happened, impact, root cause, trigger, contributing factors); the timeline and action items are ignored because every incident's look alike. A file with none of those headings is read whole.

**CSV.** A header row with a title column (`title`, `summary` or `name`) and a date column (`date`, `created`, `created_at`, `started_at` or `opened`). Optional: `id`/`key`, `severity`/`priority`, `service`/`services`/`component`, and free text in `description`, `root_cause` or `details`. This matches a default Jira issue export closely enough to use directly.

## How it works

1. **Tokenise.** Text is lower-cased, stopwords and host names are removed, and common operations vocabulary is folded together (`cert`, `certs`, `TLS` to `certificate`; `expiry`, `expired` to `expire`; `config`, `settings`, `flag` to `configuration`, and so on; the table is in `cluster.py`).
2. **Vectorise.** Each incident becomes a TF-IDF vector, so words that are rare across your incidents count for more than words every incident uses.
3. **Cluster.** Average-linkage agglomerative clustering on cosine similarity merges the most similar groups until no pair reaches the threshold. There is no random initialisation; the same input always gives the same themes.
4. **Label and summarise.** A theme is named after its three strongest terms that appear in at least half of its incidents. The summary lists the count, date range, average gap, severities and services.
5. **Trend.** Incidents are counted per quarter or month. The trend compares the later half of the periods with the earlier half: `rising`, `falling` or `steady`; `new` means every occurrence is in the latest period; `n/a` means there is only one period.

### Plugging in embeddings or a text generator

Both are optional and off by default; nothing leaves your machine unless you add one.

- **Your own embeddings** (Python API): `find_themes(incidents, threshold=..., vectors=[dense_to_vector(e) for e in embeddings])` clusters on vectors you supply, one per incident, from any model. Dense embeddings usually need a much higher threshold than the TF-IDF default.
- **Generated summaries** (CLI): `--summary-command COMMAND` pipes a short prompt per theme (key terms plus incident dates and titles, nothing else) to a command on stdin and appends what it prints to the factual summary. The command can be a script around a local model or any OpenAI-compatible HTTP endpoint. If it fails, the report is produced without the extra paragraph.

## Features

- [x] Import incidents from Markdown postmortems
- [x] Import incidents from CSV exports
- [x] Cluster incidents into themes (TF-IDF similarity, deterministic)
- [x] Factual summary per theme with example incidents
- [x] Trend over time per theme (quarter or month)
- [x] Reliability report in Markdown, HTML and JSON
- [x] Hooks for external embeddings and generated summaries (off by default)
- [ ] Built-in embedding model support
- [ ] Import directly from the Jira and PagerDuty APIs

## Limitations

- Similarity is based on shared words. Two incidents with the same underlying cause described in different vocabulary will not be grouped unless the words are in the synonym table; two unrelated incidents that share distinctive words can be.
- The synonym table and stopword list are English and oriented to web infrastructure.
- An incident belongs to exactly one theme. An incident that is both "config push" and "DNS" lands in whichever it resembles more.
- `--since` and `--until` filter before clustering, so a theme with one incident inside the range and four before it shows up as a one-off. Analyse the longer period if you want history to count.
- The trend labels are simple half-versus-half comparisons on small numbers. Treat them as a prompt to look, not as statistics.
- Clustering compares every pair of incidents and is comfortable up to a few thousand; it is not built for more.

## Development

```bash
pip install -e ".[dev]"
pytest
```

## Contributing

Issues and pull requests are welcome, especially additions to the synonym table backed by an example of two incidents it would have grouped, and postmortem layouts that fail to parse.

Built and maintained by [Narayana Vemburaj](https://github.com/narayana006).

## License

[MIT](LICENSE)
