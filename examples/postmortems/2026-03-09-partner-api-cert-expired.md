# Postmortem: Partner API client certificate expired

**Date:** 2026-03-09
**Severity:** SEV3
**Services:** partner-integrations

## Summary

Order sync to a partner failed for two hours because the client certificate used for mutual TLS expired.

## Root cause

The client certificate was renewed by hand each year and the reminder was assigned to someone who had changed teams, so it expired.

## Action items

- Automate renewal of partner client certificates
- Add the partner certificate to expiry monitoring
