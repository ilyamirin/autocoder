# Woodpecker Integration

The repository includes a minimal `.woodpecker.yml` pipeline that proves the
pet app and custom services are testable in CI.

## Current pipeline

- install Python dependencies
- run `pytest`

## Intended next step

Later iterations should add:

- branch and PR status reporting
- smoke tests for the demo stack
- deploy job for the live pet app
