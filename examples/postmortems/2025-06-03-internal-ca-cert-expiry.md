# Postmortem: Internal CA intermediate certificate expiry broke service mesh

**Date:** 2025-06-03
**Severity:** SEV2
**Services:** service-mesh, billing

## Summary

Calls between services in the mesh started failing mutual TLS when the intermediate certificate of the internal CA expired.

## Root cause

The intermediate certificate had a two year lifetime and no renewal reminder. Sidecars rejected every peer certificate once it expired.

## Action items

- Add expiry monitoring for the internal CA chain
- Document the certificate renewal runbook
