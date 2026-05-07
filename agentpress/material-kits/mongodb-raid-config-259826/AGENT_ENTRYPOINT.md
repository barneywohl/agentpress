# MongoDB RAID Storage Configuration for Optimal Performance

## Primary task
Use this GLM kit to extract source facts for `MongoDB` without inventing endpoints, status codes, signatures, return shapes, or credentials.

## Input contract
- target_url: https://www.mongodb.com/community/forums/t/what-type-of-raid-storage-configuration-is-recommended-for-achieving-optimal-performance-with-a-mongodb-deployment/259826
- source_facts_needed: facts listed below must be checked against the source before external use.
- approval_boundary: DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.

## Expected output schema
```json
{"source_facts": [], "citations": [], "validation_status": "pending|validated|blocked"}
```

## Source facts needed
- Specific RAID level recommendation (e.g., RAID-10, RAID-5, etc.)
- Disk throughput and IOPS numbers for the storage configuration
- Replica set and shard configuration details for the deployment

## Safe command
```bash
python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/mongodb-raid-config-259826 --json
```

## allowed-actions safety disclaimer
Allowed actions: read, validate, cite, summarize. Prohibited actions: credential access, unapproved external writes, external posting without human approval.

## Approval boundary
DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
