from __future__ import annotations

from mcp_chat import chat_once, load_runtime

def main() -> None:
    runtime = load_runtime()

    print("Server status:")
    for state in runtime.server_states:
        badge = "UP" if state.enabled else "DOWN"
        print(f"- {state.name}: {badge} | {state.summary}")
        if state.error:
            print(f"  error: {state.error}")

    prompt = input("\nAsk something for the MCP client: ").strip()
    if not prompt:
        print("No prompt provided.")
        return

    result = chat_once(prompt=prompt, history=[], runtime=runtime)
    print("\nAssistant:\n")
    print(result.assistant_text)

    if result.tool_events:
        print("\nTool activity:")
        for event in result.tool_events:
            print(f"- {event['tool']}({event['args']})")
            if "error" in event:
                print(f"  error: {event['error']}")


if __name__ == "__main__":
    main()
