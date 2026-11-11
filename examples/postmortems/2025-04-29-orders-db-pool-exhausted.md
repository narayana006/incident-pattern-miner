---
title: Orders database connection pool exhausted
date: 2025-04-29
severity: SEV2
services: [orders, checkout]
---

## Summary

Checkout requests timed out for 40 minutes because the orders service ran out of database connections.

## Root cause

A new report query held connections open for minutes. The connection pool was exhausted and every other request queued until it timed out.

## Action items

- Set a statement timeout on the orders database
- Alert on connection pool saturation
