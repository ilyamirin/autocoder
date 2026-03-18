# Kanboard Integration

This repository seeds Kanboard through the JSON-RPC API.

## What gets created

- project: `Autonomous Coding Demo`
- demo user: `Demo Operator`
- board columns:
  - `Backlog`
  - `Ready`
  - `Planning`
  - `Coding`
  - `Testing`
  - `Deploy`
  - `Done`
  - `Failed`
- demo tasks from the shared task catalog

## Entrypoint

Run:

```bash
python scripts/seed_kanboard.py
```

In Compose, the `kanboard-seed` service performs the same step after Kanboard
starts.
