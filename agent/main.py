import json
import time
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uvicorn
import logging
from dotenv import load_dotenv

from agent import Agent
from config import Config

agent: Agent | None = None
started_at = time.time()

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    global agent
    
    print("[Python] Starting websocket agent service...")
    config = Config()
    agent = Agent(config)
    print(f"[Python] Model: {config.openrouter_model}")
    print(f"[Python] Workspace: {config.workspace_path}")
    
    yield
    
    print("[Python] Shutting down...")
    if agent:
        await agent.cleanup()

app = FastAPI(
    title="Autonomous Agent Server",
    description="Simple websocket chat server with a bash-capable agent",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "model": agent.config.openrouter_model if agent else None,
        "workspace_path": agent.config.workspace_path if agent else None,
        "timestamp": int(time.time() * 1000),
        "uptime": time.time() - started_at,
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    session_id = str(uuid4())

    welcome = {
        "type": "response",
        "id": str(uuid4()),
        "payload": {"content": f"Connected to autonomous agent. Session: {session_id}", "done": True},
    }
    await websocket.send_text(json.dumps(welcome))

    try:
        while True:
            raw_message = await websocket.receive_text()
            response_id = str(uuid4())

            try:
                message = json.loads(raw_message)
                message_type = message.get("type")
                payload = message.get("payload", {}) or {}

                if message_type == "chat":
                    if not agent:
                        response = {
                            "type": "error",
                            "id": response_id,
                            "payload": {"message": "Agent not initialized", "code": "AGENT_UNAVAILABLE"},
                        }
                    else:
                        result = await agent.chat(message=payload.get("message", ""), context=payload.get("context"), session_id=session_id)
                        response = {
                            "type": "response",
                            "id": response_id,
                            "payload": {
                                "content": result.get("content", ""),
                                "toolCalls": result.get("tool_calls"),
                                "done": True,
                            },
                        }
                elif message_type == "ping":
                    response = {
                        "type": "pong",
                        "id": response_id,
                        "payload": {"timestamp": int(time.time() * 1000)},
                    }
                else:
                    response = {
                        "type": "error",
                        "id": response_id,
                        "payload": {
                            "message": f"Unknown message type: {message_type}",
                            "code": "UNKNOWN_TYPE",
                        },
                    }
            except Exception as exc:
                response = {
                    "type": "error",
                    "id": response_id,
                    "payload": {"message": str(exc), "code": "MESSAGE_ERROR"},
                }

            await websocket.send_text(json.dumps(response))
    except WebSocketDisconnect:
        return

if __name__ == "__main__":
    config = Config()
    
    print(f"[Python] Starting server on {config.host}:{config.port}")
    
    uvicorn.run(
        "main:app",
        host=config.host,
        port=config.port,
        log_level="info",
        access_log=True
    )