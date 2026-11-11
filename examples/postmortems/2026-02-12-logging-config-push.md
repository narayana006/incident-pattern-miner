# Postmortem: Logging config push filled disks on ingest nodes

**Date:** 2026-02-12
**Severity:** SEV2
**Services:** log-pipeline

## Summary

A configuration push switched every service to debug logging, which overwhelmed the ingest nodes within the hour.

## Root cause

The logging config push applied to the whole fleet at once. Nothing validated the config change and there was no staged rollout.

## Action items

- Stage logging config pushes by environment
- Add validation for log level changes in the config pipeline
