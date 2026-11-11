# Postmortem: Checkout API database connection pool too small

**Date:** 2026-03-14
**Severity:** SEV2
**Services:** checkout

## Summary

About 18% of checkout requests failed for 46 minutes with database connection pool timeouts.

## Root cause

A release cut the connection pool size from 50 to 5 per pod. Connections were exhausted under normal load.

## Action items

- Alert on database connection pool saturation
- Load test connection pool changes
