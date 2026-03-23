# Project Rules

## Scope

This repository is a minimal Python-only websocket agent server.

## Must Keep

1. Keep everything in Python.
2. Keep a single server process (`agent/src/main.py`).
3. Keep websocket chat endpoint at `WS /ws`.
4. Keep one tool only: `bash`.
5. Keep runtime inputs:
   - `OPENROUTER_API_KEY` (required)
   - `OPENROUTER_MODEL` (optional)
   - `WORKSPACE_PATH` (optional)
6. Keep local run support via `scripts/start.sh`.
7. Keep containerized run support via `Dockerfile`.
8. Keep Python test client (`test_client.py`).

## Do Not Add Back

- TypeScript/Bun services
- Multiple server processes
- File/HTTP/Python tools
- S3 mount/storage features
- Extra endpoints beyond minimal health/chat websocket use

## Coding Guidelines

- Prefer small, explicit, readable changes.
- Keep dependencies minimal.
- Validate syntax after changes.
- Don't add comments
- Don't try catch unless there is a reason
- Don't add docstrings unless mentioned
