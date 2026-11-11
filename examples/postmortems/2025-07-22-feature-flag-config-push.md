---
title: Feature flag config push disabled checkout
date: 2025-07-22
severity: SEV1
services: [checkout]
---

## Summary

A feature flag configuration push turned off the payment form for all shoppers for 12 minutes.

## Root cause

The flag config push went to all environments at the same time. The config file had a typo that validation did not catch, and there was no staged rollout.

## Action items

- Add schema validation to the flag config pipeline
- Stage flag config pushes behind a canary
