# Search index corrupted during reindex

Severity: SEV3
Services: search

## What happened

Search results were incomplete for four hours after a reindex job was interrupted halfway.

## Root cause

The reindex job wrote directly to the live index and was killed by a node replacement, leaving a partial index.

## Action items

- Build new indexes offline and swap an alias
