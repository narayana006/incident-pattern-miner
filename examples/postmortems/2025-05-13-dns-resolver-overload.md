# Cluster DNS resolver overload

Severity: SEV2
Services: kubernetes

## What happened

Service discovery lookups in the main cluster failed intermittently for an hour.

## Root cause

A batch job generated a flood of DNS queries and the cluster DNS resolver pods were overloaded. DNS lookups failed for unrelated workloads.

## Action items

- Scale the DNS resolver with cluster size
- Enable a node-local DNS cache
