# Postmortem: Bad rate limit config push throttled all traffic

**Date:** 2025-03-18
**Severity:** SEV1
**Services:** api-gateway

## Summary

A configuration push set the global rate limit to 10 requests per second, so most API requests were rejected with 429 for 17 minutes.

## Root cause

The config change was pushed to every region at once with no validation of the new limit and no staged rollout.

## Action items

- Validate rate limit values before a config push
- Roll config changes out one region at a time
