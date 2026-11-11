# Postmortem: Third-party payment provider outage

**Date:** 2026-01-08
**Severity:** SEV2
**Services:** payments

## Summary

Card payments failed for 50 minutes while the payment provider had an outage of its own.

## Root cause

The provider's API returned errors and our integration has no secondary provider to fall back to.

## Action items

- Evaluate a fallback payment provider
