# MCP Multi-Server Client

This project now includes:

- A local Math MCP server in [main.py](/Users/shreyashgolhani/Desktop/mcp-client/main.py)
- A reusable MCP chat runtime in [mcp_chat.py](/Users/shreyashgolhani/Desktop/mcp-client/mcp_chat.py)
- A simple CLI client in [client1.py](/Users/shreyashgolhani/Desktop/mcp-client/client1.py)
- A Streamlit chatbot UI in [streamlit_app.py](/Users/shreyashgolhani/Desktop/mcp-client/streamlit_app.py)

## What Was Broken

The original setup had two main issues:

- `main.py` was only a placeholder, so the local Math MCP server could not start.
- The Manim server path in `client1.py` pointed to `/Users/nitish/...`, which does not exist on this machine. That caused MCP tool discovery to fail and crash the whole client.

The new runtime loads each server separately and marks broken ones as unavailable instead of stopping the whole app.

## Environment

Create a `.env` file with at least one of these:

```env
GROQ_API_KEY=your_groq_key
```


Optional Manim settings:

```env
MANIM_MCP_SERVER_PATH=/absolute/path/to/manim_server.py
MANIM_MCP_PYTHON=/absolute/path/to/python
MANIM_EXECUTABLE=/absolute/path/to/manim
EXPENSE_MCP_URL=https://splendid-gold-dingo.fastmcp.app/mcp
```

## Run

CLI:

```bash
.venv/bin/python client1.py
```

Streamlit:

```bash
.venv/bin/streamlit run streamlit_app.py
```

For Streamlit deployment, use `streamlit_app.py` as the app entry point.
