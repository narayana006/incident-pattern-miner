# Auth database hit max connections

Severity: SEV1
Services: auth

## What happened

Logins failed for 15 minutes when the auth database reached its maximum number of connections.

## Root cause

A deploy doubled the number of pods without lowering the per-pod connection pool size, so the database connection limit was exhausted.

## Action items

- Put a connection pooler in front of the auth database
- Review pool size whenever replica counts change
