---
title: API gateway certificate expired
date: 2025-02-11
severity: SEV1
services: [api-gateway]
---

## Summary

All HTTPS traffic to api.example.com failed TLS handshakes for 38 minutes because the gateway certificate expired.

## Root cause

The certificate was issued manually a year ago and its expiry was tracked in a spreadsheet nobody owned. Automatic renewal was never set up for this hostname.

## Action items

- Move api.example.com to automated certificate renewal
- Alert 21 days before any certificate expires
