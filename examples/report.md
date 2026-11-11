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

### 2. configuration / push / staged

5 incidents between 2025-03-18 and 2026-02-12. Average gap between occurrences: 83 days. Severity: SEV1 x2, SEV2 x3. Services involved: api-gateway (1), checkout (1), load-balancer (1), log-pipeline (1), search (1).

Key terms: configuration, push, staged, deploy, validation, change

- 2026-02-12 [SEV2] Logging config push filled disks on ingest nodes (`2026-02-12-logging-config-push`)
- 2025-11-05 [SEV2] Load balancer config push dropped a backend pool (`2025-11-05-lb-config-push`)
- 2025-09-30 [SEV2] Cache config push evicted all sessions (`OPS-1577`)
- 2025-07-22 [SEV1] Feature flag config push disabled checkout (`2025-07-22-feature-flag-config-push`)
- 2025-03-18 [SEV1] Bad rate limit config push throttled all traffic (`2025-03-18-rate-limit-config-push`)

### 3. connection / database / pool

4 incidents between 2025-04-29 and 2026-03-14. Average gap between occurrences: 106 days. Severity: SEV1 x1, SEV2 x2, SEV3 x1. Services involved: checkout (2), auth (1), orders (1), reporting (1).

Key terms: connection, database, pool, exhausted, timeout, checkout

- 2026-03-14 [SEV2] Checkout API database connection pool too small (`2026-03-14-checkout-db-pool`)
- 2025-12-17 [SEV3] Reporting database out of connections (`OPS-1603`)
- 2025-09-16 [SEV1] Auth database hit max connections (`2025-09-16-auth-db-connections`)
- 2025-04-29 [SEV2] Orders database connection pool exhausted (`2025-04-29-orders-db-pool-exhausted`)

### 4. dns / lookup

2 incidents between 2025-05-13 and 2025-12-02. Average gap between occurrences: 203 days. Severity: SEV1 x1, SEV2 x1. Services involved: all (1), dns (1), kubernetes (1).

Key terms: dns, lookup

- 2025-12-02 [SEV1] DNS zone change removed internal records (`2025-12-02-dns-zone-change`)
- 2025-05-13 [SEV2] Cluster DNS resolver overload (`2025-05-13-dns-resolver-overload`)

## One-off incidents

- 2025-08-07 [SEV3] Search index corrupted during reindex (`2025-08-07-search-index-corruption`)
- 2026-01-08 [SEV2] Third-party payment provider outage (`2026-01-08-payment-provider-outage`)
- 2026-02-03 [SEV4] Office VPN concentrator failed over (`OPS-1650`)
