# Load balancer config push dropped a backend pool

Severity: SEV2
Services: load-balancer, search

## What happened

Search returned 502 errors for 21 minutes after a load balancer configuration push removed a healthy backend pool.

## Root cause

A config template change was pushed globally without a dry run or validation step, and the staged rollout was skipped to save time.

## Action items

- Make dry-run validation mandatory for load balancer config
- Remove the option to skip the staged config rollout
