---
title: DNS zone change removed internal records
date: 2025-12-02
severity: SEV1
services: [dns, all]
---

## Summary

Internal hostnames stopped resolving for 28 minutes after a DNS zone migration.

## Root cause

The DNS zone migration script left out the internal records, so DNS lookups for internal hostnames returned NXDOMAIN.

## Action items

- Diff DNS records before and after any zone migration
- Keep the old DNS zone available for rollback
