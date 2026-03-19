# Kanboard Integration

This repository seeds Kanboard through the JSON-RPC API.

The live Kanboard UI is also customized through the repo-local `GcgTheme`
plugin mounted from `infra/kanboard/plugins/GcgTheme`.

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

## Theme Plugin

The board theme is implemented as a plugin instead of a Kanboard core fork:

- plugin directory: `infra/kanboard/plugins/GcgTheme`
- copied into `/var/www/app/plugins/GcgTheme` on container start
- overrides:
  - `auth/index`
  - `header`
- injects:
  - `plugins/GcgTheme/Assets/css/gcg.css`
  - `template:layout:top` banner
