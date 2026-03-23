# Autonomous Agent (Python Only)

Simple websocket chat server in Python with a single bash tool.

## Features

- One Python websocket server (`WS /ws`)
- One health endpoint (`GET /health`)
- One agent tool: `bash`
- OpenRouter model via `pydantic-ai`
- Works locally and in Docker

## Required Inputs

- `OPENROUTER_API_KEY` (required)
- `OPENROUTER_MODEL` (optional, default `moonshotai/kimi-k2.5`)
- `WORKSPACE_PATH` (optional, default `./workspace` locally or `/workspace` in Docker)

## Local Run

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r agent/requirements.txt

OPENROUTER_API_KEY="your-key" \
OPENROUTER_MODEL="moonshotai/kimi-k2.5" \
WORKSPACE_PATH="$PWD/workspace" \
bash scripts/start.sh
```

## Docker Run

Build image:

```bash
docker build -t autonomous-agent .
```

Run one agent:

```bash
docker run --rm -p 8000:8000 \
  -e OPENROUTER_API_KEY="your-key" \
  -e OPENROUTER_MODEL="moonshotai/kimi-k2.5" \
  -e WORKSPACE_PATH="/workspace" \
  -v "$PWD/workspace:/workspace" \
  autonomous-agent
```

Run multiple isolated agents:

```bash
docker run --rm -p 8001:8000 -e OPENROUTER_API_KEY="your-key" -v "$PWD/ws1:/workspace" autonomous-agent
docker run --rm -p 8002:8000 -e OPENROUTER_API_KEY="your-key" -v "$PWD/ws2:/workspace" autonomous-agent
```

Each container gets isolated filesystem via a different mounted workspace.

## Test Client (Python)

```bash
python3 test_client.py --ws-url ws://localhost:8000/ws
```

Commands:
- normal text: send chat
- `/ping`: send ping
- `/quit`: exit