---
title: CDN certificate renewal failed and certificate expired
date: 2026-01-27
severity: SEV2
services: [cdn, web]
---

## Summary

Static assets for www.example.com were served with an expired certificate, so browsers blocked the site for 25 minutes.

## Root cause

Automated renewal failed DNS validation after a zone change, and the expiry alert went to a mailbox no one reads. The certificate expired on schedule.

## Action items

- Route certificate expiry alerts to the on-call rotation
- Test renewal after every DNS zone change
