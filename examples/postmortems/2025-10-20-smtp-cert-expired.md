# Outbound email stopped: SMTP relay certificate expired

Severity: SEV3
Services: notifications

## What happened

Password reset and receipt emails were not delivered for three hours after the SMTP relay certificate expired.

## Root cause

The relay's certificate renewal job had been failing silently for weeks, so the certificate expired without anyone being told.

## Action items

- Alert when a certificate renewal job fails
- Add the relay to the certificate expiry dashboard
