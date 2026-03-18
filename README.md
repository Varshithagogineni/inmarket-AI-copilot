# Event Surge Activation Copilot

Monorepo scaffold for an agentic marketing copilot that:

- discovers relevant local events
- evaluates the best-fit activation opportunity
- generates a campaign brief
- produces draft copy and visual creative inputs

## Apps

- `apps/api`: FastAPI application and orchestration layer
- `apps/mcp`: FastMCP tool server for external capabilities
- `apps/web`: React user interface

## Shared packages

- `packages/shared-schemas`: shared JSON schema and example payloads

## Current status

This repository contains the initial architecture scaffold, domain logic, UI skeleton, and testable core scoring/orchestration utilities. External dependencies are declared but not installed in this environment.

## Validation run in this environment

- Python workflow unit tests:
  - `& 'C:\Program Files\Salt Project\Salt\bin\python.exe' -m unittest app.tests.test_workflow`
- Node scaffold validation:
  - `node tests/validate-scaffold.mjs`

Current backend and MCP test count: `19`

## Local persistence modes

- `RUN_REPOSITORY=memory` keeps runs in-process for lightweight local work
- `RUN_REPOSITORY=file` with `RUN_STORAGE_PATH=data/runs.json` persists runs between sessions
