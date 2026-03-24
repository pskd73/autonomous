import json
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, AsyncIterator

from config import Config
from bash import BashTool
from memory import MemoryInterface

from pydantic_ai import Agent as PydanticAgent
from pydantic_ai import RunContext


@dataclass
class AgentDeps:
    config: Config
    tools: Dict[str, Any]
    context: Optional[Dict[str, Any]] = None
    tool_results: list[Dict[str, Any]] = field(default_factory=list)


class Agent:
    def __init__(self, config: Config):
        self.config = config

        self.tools = {
            "bash": BashTool(config),
        }

        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.memories: Dict[str, MemoryInterface] = {}

        self.pydantic_agent = PydanticAgent(
            f"openrouter:{self.config.openrouter_model}",
            deps_type=AgentDeps,
            instructions=(
                "You are a helpful autonomous agent with one available tool: bash. "
                "bash tool is used to execute bash commands on the system."
                "Always use bash tool when it helps answer the user."
                "Use linux commands from bash tool."
                "You are on a linux machine and can run linux commands."
                "You work from the /workspace directory."
            ),
        )
        
        @self.pydantic_agent.tool
        async def bash(
            ctx: RunContext[AgentDeps],
            command: str,
            cwd: Optional[str] = None,
            timeout: int = 60,
        ) -> Dict[str, Any]:
            result = await ctx.deps.tools["bash"].execute(command, cwd=cwd, timeout=timeout)
            ctx.deps.tool_results.append(
                {"name": "bash", "arguments": {"command": command, "cwd": cwd}, "result": result}
            )
            return result
    
    async def chat(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Unified chat interface.

        Yields events:
        - {"type": "delta", "content": "<text>"}
        - {"type": "final", "result": {...}}
        """
        session_key = session_id or "default"

        if session_key not in self.sessions:
            self.sessions[session_key] = {
                "message_history": [],
            }

        session = self.sessions[session_key]
        message_history = session.get("message_history", [])

        prompt = message
        if context:
            prompt = f"{message}\n\nContext:\n{json.dumps(context, indent=2, default=str)}"

        for key, memory in self.memories.items():
            prompt = f"{prompt}\n\nMemory ({key}):\n{memory.recall(key)}"

        deps = AgentDeps(config=self.config, tools=self.tools, context=context)

        full_output_parts: list[str] = []

        async with self.pydantic_agent.run_stream(
            prompt,
            deps=deps,
            message_history=message_history if message_history else None,
        ) as streamed_result:
            async for delta in streamed_result.stream_text(delta=True, debounce_by=None):
                if delta:
                    full_output_parts.append(delta)
                    yield {"type": "delta", "content": delta}

            last_messages = streamed_result.all_messages()

        full_output = "".join(full_output_parts)
        for key, memory in self.memories.items():
            memory.memorise(message, full_output)

        session["message_history"] = last_messages
        yield {
            "type": "final",
            "result": {
                "content": full_output,
                "tool_calls": deps.tool_results if deps.tool_results else None,
                "session_id": session_key,
            },
        }

    async def cleanup(self):
        return
        