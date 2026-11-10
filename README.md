# incident-pattern-miner

Cluster past incidents by theme to find repeat failure modes and produce quarterly reliability reports.

> **Project status: planning. There is no working code in this repository yet.**
> This README describes what the project will do. Nothing below can be installed or run today.
> Features are ticked off in the checklist as they are built.

## What it is

A command-line tool.

**The problem it solves:** The same failure modes (cert expiry, config pushes) recur because nobody looks across incidents.

## Who it is for

Reliability teams who want to know which kinds of failure keep coming back.

## How it will work

1. You import past incidents from Markdown files, a ticket system or CSV.
2. The tool groups similar incidents into themes and writes a short summary of each.
3. It produces a report showing how often each theme occurs and how that changes over time.

## Planned features

Unticked items are not built yet.

- [ ] Import incidents from Markdown, Jira, PagerDuty or CSV
- [ ] Embedding-based clustering into themes
- [ ] LLM summary per theme with example incidents
- [ ] Trend over time per theme
- [ ] Quarterly reliability report (Markdown / HTML)

## Planned usage

This is the intended interface, shown so you can judge the design. **It does not work yet**, and names may change before the first release.

```bash
incident-pattern-miner analyze ./postmortems --since 2026-01-01
```

## Contributing

Feedback on the design is the most useful contribution right now. Open an issue to suggest a feature, question an approach or describe your use case. Code contributions are welcome once the first version lands.

## Author

Built and maintained by [Narayana Vemburaj](https://github.com/narayana006).

## License

[MIT](LICENSE)
