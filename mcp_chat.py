from __future__ import annotations

import asyncio
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_groq import ChatGroq
from langchain_mcp_adapters.client import MultiServerMCPClient

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
LOCAL_MATH_SERVER = BASE_DIR / "main.py"
LOCAL_VENV_PYTHON = BASE_DIR / ".venv" / "bin" / "python"
MAX_TOOL_ROUNDS = 6


@dataclass(slots=True)
class ServerState:
    name: str
    enabled: bool
    transport: str
    summary: str
    error: str | None = None


@dataclass(slots=True)
class RuntimeState:
    connections: dict[str, dict[str, Any]]
    server_states: list[ServerState]
    tools: list[Any]
    named_tools: dict[str, Any]


@dataclass(slots=True)
class ChatTurnResult:
    history: list[BaseMessage]
    assistant_text: str
    tool_events: list[dict[str, Any]]


def run_async(coro: Any) -> Any:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def build_connections() -> tuple[dict[str, dict[str, Any]], list[ServerState]]:
    connections: dict[str, dict[str, Any]] = {}
    server_states: list[ServerState] = []

    python_command = str(LOCAL_VENV_PYTHON if LOCAL_VENV_PYTHON.exists() else Path(sys.executable))
    connections["math"] = {
        "transport": "stdio",
        "command": python_command,
        "args": [str(LOCAL_MATH_SERVER)],
    }
    server_states.append(
        ServerState(
            name="math",
            enabled=True,
            transport="stdio",
            summary="Local Math server from this project.",
        )
    )

    expense_url = os.getenv("EXPENSE_MCP_URL").strip()
    connections["expense"] = {
        "transport": "streamable_http",
        "url": expense_url,
    }
    server_states.append(
        ServerState(
            name="expense",
            enabled=True,
            transport="streamable_http",
            summary=f"Remote Expense Tracker at {expense_url}.",
        )
    )

    manim_server_path = os.getenv("MANIM_MCP_SERVER_PATH", "").strip()
    if manim_server_path:
        server_path = Path(manim_server_path).expanduser()
        if server_path.exists():
            manim_python = os.getenv("MANIM_MCP_PYTHON", python_command).strip() or python_command
            env = {}
            manim_executable = os.getenv("MANIM_EXECUTABLE", "").strip()
            if manim_executable:
                env["MANIM_EXECUTABLE"] = manim_executable

            connections["manim"] = {
                "transport": "stdio",
                "command": manim_python,
                "args": [str(server_path)],
                **({"env": env} if env else {}),
            }
            server_states.append(
                ServerState(
                    name="manim",
                    enabled=True,
                    transport="stdio",
                    summary=f"Configured Manim server at {server_path}.",
                )
            )
        else:
            server_states.append(
                ServerState(
                    name="manim",
                    enabled=False,
                    transport="stdio",
                    summary="Manim server path is configured but missing.",
                    error=f"File not found: {server_path}",
                )
            )
    else:
        server_states.append(
            ServerState(
                name="manim",
                enabled=False,
                transport="stdio",
                summary="Set MANIM_MCP_SERVER_PATH to enable the Manim server.",
            )
        )

    return connections, server_states


def _tool_result_to_text(result: Any) -> str:
    if isinstance(result, str):
        return result
    try:
        return json.dumps(result, indent=2, ensure_ascii=True, default=str)
    except TypeError:
        return str(result)


def _format_exception(exc: BaseException) -> str:
    if isinstance(exc, BaseExceptionGroup) and exc.exceptions:
        return _format_exception(exc.exceptions[0])

    if exc.__cause__ is not None:
        cause_text = _format_exception(exc.__cause__)
        if cause_text:
            return cause_text

    text = str(exc).strip()
    return text or exc.__class__.__name__


def _llm_api_key() -> str | None:
    return os.getenv("GROQ_API_KEY")


def make_llm() -> ChatGroq:
    api_key = _llm_api_key()
    if not api_key:
        raise RuntimeError(
            "Missing Groq API key. Set GROQ_API_KEY in your .env file."
        )

    return ChatGroq(
        model=os.getenv("GROQ_MODEL"),
        api_key=api_key,
        temperature=0,
    )


async def create_runtime() -> RuntimeState:
    connections, server_states = build_connections()
    client = MultiServerMCPClient(connections, tool_name_prefix=True)

    tools: list[Any] = []
    named_tools: dict[str, Any] = {}
    state_lookup = {state.name: state for state in server_states}

    for server_name in connections:
        try:
            server_tools = await client.get_tools(server_name=server_name)
            tools.extend(server_tools)
            named_tools.update({tool.name: tool for tool in server_tools})
            tool_names = ", ".join(tool.name for tool in server_tools) or "No tools exposed"
            state_lookup[server_name].summary = (
                f"{state_lookup[server_name].summary} Tools: {tool_names}."
            )
        except Exception as exc:
            state_lookup[server_name].enabled = False
            state_lookup[server_name].error = _format_exception(exc)

    return RuntimeState(
        connections=connections,
        server_states=server_states,
        tools=tools,
        named_tools=named_tools,
    )


async def chat_with_mcp(
    prompt: str,
    history: list[BaseMessage] | None = None,
    runtime: RuntimeState | None = None,
) -> ChatTurnResult:
    chat_history = list(history or [])
    llm = make_llm()

    active_runtime = runtime or await create_runtime()
    messages: list[BaseMessage] = [*chat_history, HumanMessage(content=prompt)]
    tool_events: list[dict[str, Any]] = []

    if not active_runtime.tools:
        response = await llm.ainvoke(messages)
        return ChatTurnResult(
            history=[*messages, response],
            assistant_text=str(response.content),
            tool_events=tool_events,
        )

    llm_with_tools = llm.bind_tools(active_runtime.tools)

    for _ in range(MAX_TOOL_ROUNDS):
        response = await llm_with_tools.ainvoke(messages)
        messages.append(response)

        if not getattr(response, "tool_calls", None):
            return ChatTurnResult(
                history=messages,
                assistant_text=str(response.content),
                tool_events=tool_events,
            )

        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call.get("args") or {}

            event: dict[str, Any] = {"tool": tool_name, "args": tool_args}
            tool_events.append(event)

            tool = active_runtime.named_tools.get(tool_name)
            if tool is None:
                error_text = f"Tool '{tool_name}' is not available."
                event["error"] = error_text
                messages.append(
                    ToolMessage(
                        tool_call_id=tool_call["id"],
                        content=json.dumps({"error": error_text}),
                    )
                )
                continue

            try:
                result = await tool.ainvoke(tool_args)
                event["result"] = result
                messages.append(
                    ToolMessage(
                        tool_call_id=tool_call["id"],
                        content=_tool_result_to_text(result),
                    )
                )
            except Exception as exc:
                error_text = _format_exception(exc)
                event["error"] = error_text
                messages.append(
                    ToolMessage(
                        tool_call_id=tool_call["id"],
                        content=json.dumps({"error": error_text}),
                    )
                )

    fallback = AIMessage(
        content=(
            "I reached the maximum number of tool rounds before finishing the reply. "
            "Please refine the request and try again."
        )
    )
    messages.append(fallback)
    return ChatTurnResult(
        history=messages,
        assistant_text=str(fallback.content),
        tool_events=tool_events,
    )


def chat_once(prompt: str, history: list[BaseMessage], runtime: RuntimeState) -> ChatTurnResult:
    return run_async(chat_with_mcp(prompt=prompt, history=history, runtime=runtime))


def load_runtime() -> RuntimeState:
    return run_async(create_runtime())
