# incident-pattern-miner

> Cluster past incidents by theme to find repeat failure modes and produce quarterly reliability reports.

**Status:** 🚧 Early stage — design and roadmap published, implementation in progress. Stars, issues and ideas welcome.

## Why

The same failure modes (cert expiry, config pushes) recur because nobody looks across incidents.

## Planned features

- [ ] Import incidents from Markdown, Jira, PagerDuty or CSV
- [ ] Embedding-based clustering into themes
- [ ] LLM summary per theme with example incidents
- [ ] Trend over time per theme
- [ ] Quarterly reliability report (Markdown / HTML)

## Intended usage

```
incident-pattern-miner analyze ./postmortems --since 2026-01-01
```

_The interface above is the target design and may change._

## Roadmap

1. Core implementation of the first feature set
2. Examples and tests
3. CI and first tagged release
4. Docs and integrations

## Contributing

Contributions are welcome. Open an issue to discuss an idea or pick an unchecked item from the feature list.

## License

[MIT](LICENSE)
