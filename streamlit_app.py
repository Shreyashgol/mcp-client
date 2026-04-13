from __future__ import annotations

import os

import streamlit as st

from mcp_chat import ChatTurnResult, DEFAULT_MODEL, load_runtime

st.set_page_config(
    page_title="MCP Multi-Server Chat",
    page_icon="🤖",
    layout="centered",
)


@st.cache_resource(show_spinner=False)
def get_runtime():
    return load_runtime()


def init_state() -> None:
    if "history" not in st.session_state:
        st.session_state.history = []
    if "chat_log" not in st.session_state:
        st.session_state.chat_log = [
            {
                "role": "assistant",
                "content": (
                    "Welcome. Ask about math, expense tracking, or Manim animations, "
                    "and I will use the MCP servers that are available."
                ),
                "tool_events": [],
            }
        ]


def clear_chat() -> None:
    st.session_state.history = []
    st.session_state.chat_log = [
        {
            "role": "assistant",
            "content": (
                "Chat cleared. Ask a new question and I will use the connected MCP servers."
            ),
            "tool_events": [],
        }
    ]


def render_sidebar() -> None:
    runtime = get_runtime()

    st.sidebar.title("MCP Client")
    st.sidebar.write("Standard Streamlit chat UI for multiple MCP servers.")

    if st.sidebar.button("Refresh Servers", use_container_width=True):
        get_runtime.clear()
        st.rerun()

    if st.sidebar.button("Clear Chat", use_container_width=True):
        clear_chat()
        st.rerun()

    st.sidebar.subheader("Configuration")
    st.sidebar.caption("Required: `GROQ_API_KEY` or `groq_api` in `.env`.")
    st.sidebar.caption("Optional: `MANIM_MCP_SERVER_PATH`, `MANIM_MCP_PYTHON`, `MANIM_EXECUTABLE`.")

    st.sidebar.subheader("Servers")
    for state in runtime.server_states:
        label = "Online" if state.enabled else "Offline"
        text = f"**{state.name}**: {label}\n\n{state.summary}"
        if state.error:
            st.sidebar.error(f"{text}\n\nError: {state.error}")
        elif state.enabled:
            st.sidebar.success(text)
        else:
            st.sidebar.info(text)


def render_header() -> None:
    runtime = get_runtime()
    active_servers = sum(1 for state in runtime.server_states if state.enabled)

    st.title("MCP Multi-Server Chat")
    st.write(
        "Deploy this app with Streamlit to chat with your local Math server, "
        "remote Expense Tracker server, and optional Manim server from one place."
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("Active Servers", active_servers)
    col2.metric("Discovered Tools", len(runtime.tools))
    col3.metric("Model", os.getenv("GROQ_MODEL", DEFAULT_MODEL))

    if not (os.getenv("GROQ_API_KEY") or os.getenv("groq_api")):
        st.warning("Add `GROQ_API_KEY` or `groq_api` to `.env` before sending chat requests.")

    with st.expander("Example Prompts", expanded=False):
        st.markdown("- Calculate the area of a circle with radius 8.")
        st.markdown("- Show my total expenses for this month.")
        st.markdown("- Create a Manim animation of a rotating triangle.")


def render_chat_log() -> None:
    for entry in st.session_state.chat_log:
        with st.chat_message(entry["role"]):
            st.markdown(entry["content"])
            for event in entry.get("tool_events", []):
                with st.expander(f"Tool Call: {event['tool']}", expanded=False):
                    st.json({"args": event["args"]})
                    if "result" in event:
                        st.json({"result": event["result"]})
                    if "error" in event:
                        st.error(event["error"])


def run_turn(prompt: str) -> ChatTurnResult:
    runtime = get_runtime()
    from mcp_chat import chat_once

    return chat_once(prompt=prompt, history=st.session_state.history, runtime=runtime)


def append_turn(prompt: str, result: ChatTurnResult) -> None:
    st.session_state.history = result.history
    st.session_state.chat_log.append(
        {"role": "user", "content": prompt, "tool_events": []}
    )
    st.session_state.chat_log.append(
        {
            "role": "assistant",
            "content": result.assistant_text,
            "tool_events": result.tool_events,
        }
    )


def main() -> None:
    init_state()
    render_sidebar()
    render_header()
    render_chat_log()

    prompt = st.chat_input("Ask something...")
    if not prompt:
        return

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                result = run_turn(prompt)
            except Exception as exc:
                st.error(str(exc))
                return

        st.markdown(result.assistant_text)
        for event in result.tool_events:
            with st.expander(f"Tool Call: {event['tool']}", expanded=False):
                st.json({"args": event["args"]})
                if "result" in event:
                    st.json({"result": event["result"]})
                if "error" in event:
                    st.error(event["error"])

    append_turn(prompt, result)


if __name__ == "__main__":
    main()
