import json
import time
from typing import Any
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _extract_message_text(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, dict):
                text = part.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(parts).strip()
    return ""


def _last_user_message(messages: list[dict[str, Any]]) -> str:
    for message in reversed(messages):
        if message.get("role") == "user":
            text = _extract_message_text(message.get("content"))
            if text:
                return text
    return ""


def _chunk_text(text: str, size: int = 160) -> list[str]:
    if not text:
        return []
    return [text[i : i + size] for i in range(0, len(text), size)]


async def _collect_chat_result(
    message: str,
    session_id: str,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    final_result: dict[str, Any] | None = None
    async for event in agent.chat(message=message, context=context, session_id=session_id):
        if event.get("type") == "final":
            final_result = event.get("result")
    if not final_result:
        return {"content": "", "tool_calls": None, "session_id": session_id}
    return final_result


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "model": agent.config.openrouter_model if agent else None,
        "workspace_path": agent.config.workspace_path if agent else None,
        "timestamp": int(time.time() * 1000),
        "uptime": time.time() - started_at,
    }


@app.get("/v1/models")
async def openai_models():
    model_name = agent.config.openrouter_model if agent else "unknown"
    return {
        "object": "list",
        "data": [
            {
                "id": model_name,
                "object": "model",
                "created": int(started_at),
                "owned_by": "openrouter",
            }
        ],
    }


@app.post("/v1/chat/completions")
async def openai_chat_completions(request: Request):
    """OpenAI-compatible chat completions endpoint with streaming support."""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    messages = body.get("messages")
    if not isinstance(messages, list):
        raise HTTPException(status_code=400, detail="Invalid payload: messages must be an array")

    user_message = _last_user_message(messages)
    if not user_message:
        raise HTTPException(status_code=400, detail="No user message found")

    stream = bool(body.get("stream", False))
    session_id = request.headers.get("x-session-id") or body.get("user") or "default"

    model_name = agent.config.openrouter_model
    created = int(time.time())
    completion_id = f"chatcmpl-{uuid4().hex}"

    if stream:
        async def event_stream():
            first = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model_name,
                "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}],
            }
            yield f"data: {json.dumps(first)}\n\n"

            try:
                async for event in agent.chat(message=user_message, session_id=str(session_id)):
                    if event.get("type") != "delta":
                        continue
                    delta = event.get("content", "")
                    if delta:
                        chunk = {
                            "id": completion_id,
                            "object": "chat.completion.chunk",
                            "created": created,
                            "model": model_name,
                            "choices": [{"index": 0, "delta": {"content": delta}, "finish_reason": None}],
                        }
                        yield f"data: {json.dumps(chunk)}\n\n"
            except Exception as exc:
                error_chunk = {
                    "id": completion_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": model_name,
                    "choices": [{"index": 0, "delta": {"content": f"\n[error] {str(exc)}"}, "finish_reason": None}],
                }
                yield f"data: {json.dumps(error_chunk)}\n\n"

            final = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model_name,
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
            }
            yield f"data: {json.dumps(final)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache"},
        )

    result = await _collect_chat_result(message=user_message, session_id=str(session_id))
    content = result.get("content", "")

    response = {
        "id": completion_id,
        "object": "chat.completion",
        "created": created,
        "model": model_name,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
    }
    return JSONResponse(response)
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
                        result = await _collect_chat_result(
                            message=payload.get("message", ""),
                            context=payload.get("context"),
                            session_id=session_id,
                        )
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