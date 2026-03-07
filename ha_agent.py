"""
ha_agent.py

A smarter Home Assistant agent that solves two problems with the basic approach:

  Problem 1 — The model doesn't know your entity IDs.
    When you say "turn off the office lights", the model needs to know the
    entity ID is "light.office1_light", not just guess. We fix this by
    fetching all your devices on startup and injecting a name→ID map into
    the system prompt.

  Problem 2 — 89 tools overwhelms the model.
    With too many choices, the model picks the wrong tool or gives up.
    We fix this by only passing the 8 most useful tools for daily control.

Usage:
    import asyncio
    from ha_agent import run, load_context

    async def main():
        await load_context()          # call once at startup
        reply = await run("turn off the office lights")
        print(reply)
"""

import asyncio
import os

import ollama
from dotenv import load_dotenv

from ha_mcp_client import call_tool, get_tools

load_dotenv()

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3.5:9b")

# These are the only tools we expose to the model.
# Fewer tools = faster, more accurate tool selection.
ALLOWED_TOOLS = {
    "ha_search_entities",   # find entities by name or domain
    "ha_get_state",         # check if a device is on/off, get sensor reading
    "ha_get_states",        # check multiple devices at once
    "ha_call_service",      # turn on/off, set brightness, set temperature, etc.
    "ha_bulk_control",      # control multiple devices in one call
    "ha_get_overview",      # general home status summary
    "ha_get_history",       # was a device on/off at a certain time?
    "ha_list_services",     # discover what services a domain supports
}

# This gets populated by load_context() at startup.
# It holds a human-readable map of your devices (name → entity_id).
_entity_context = ""

# Base system prompt — entity context gets appended to this at startup.
_BASE_PROMPT = """You are a Home Assistant controller with full access to the user's smart home.

RULES — follow these exactly:
- ALWAYS use tools. Never say you "can't" or "don't have access" — you do.
- Use the entity list below to find the correct entity_id before calling ha_call_service.
- To turn a device on/off: call ha_call_service with the correct domain and entity_id.
  Example: domain="light", service="turn_off", entity_id="light.office1_light"
- To check a device state: use ha_get_state with the entity_id.
- If you're unsure of an entity_id: use ha_search_entities first.
- Be concise: one sentence to confirm success, or report what you found briefly.
"""


async def load_context() -> None:
    """
    Fetch all devices from Home Assistant and build an entity map.
    Call this once at startup before handling any messages.

    This gives the model a concrete name→entity_id reference so it doesn't
    have to guess entity IDs when calling ha_call_service.
    """
    global _entity_context

    print("Loading Home Assistant entity context...")

    try:
        # ha_get_overview returns a summary of all entities grouped by domain
        overview_result = await call_tool("ha_get_overview", {})

        # Also get lights and switches specifically for a clean list
        lights_result = await call_tool("ha_search_entities", {
            "query": "light",
            "domain": "light",
        })
        switches_result = await call_tool("ha_search_entities", {
            "query": "",
            "domain": "switch",
        })
        climate_result = await call_tool("ha_search_entities", {
            "query": "",
            "domain": "climate",
        })

        _entity_context = (
            "\n\nHOME ASSISTANT ENTITY REFERENCE:\n"
            "Use these entity_ids when calling ha_call_service.\n\n"
            f"LIGHTS:\n{lights_result}\n\n"
            f"SWITCHES:\n{switches_result}\n\n"
            f"CLIMATE:\n{climate_result}\n\n"
            f"OVERVIEW:\n{overview_result[:1000]}\n"
        )
        print("Entity context loaded.")

    except Exception as e:
        print(f"Warning: could not load entity context: {e}")
        _entity_context = ""


def _build_system_prompt() -> str:
    """Combine the base prompt with the current entity context."""
    return _BASE_PROMPT + _entity_context


def _filter_tools(all_tools: list[dict]) -> list[dict]:
    """Return only the tools in ALLOWED_TOOLS."""
    return [
        t for t in all_tools
        if t["function"]["name"] in ALLOWED_TOOLS
    ]


async def run(user_message: str) -> str:
    """
    Process a user's message and return the AI's final reply.
    Call load_context() at least once before calling this.
    """
    all_tools = await get_tools()
    tools = _filter_tools(all_tools)

    messages = [
        {"role": "system", "content": _build_system_prompt()},
        {"role": "user", "content": user_message},
    ]

    MAX_ITERATIONS = 10
    for _ in range(MAX_ITERATIONS):
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=messages,
            tools=tools,
        )

        assistant_message = response.message
        messages.append(assistant_message)

        if not assistant_message.tool_calls:
            return assistant_message.content or "Done."

        for tool_call in assistant_message.tool_calls:
            tool_name = tool_call.function.name
            tool_args = tool_call.function.arguments or {}

            print(f"  → Calling tool: {tool_name}({tool_args})")

            try:
                result = await call_tool(tool_name, tool_args)
            except Exception as e:
                result = f"Error calling {tool_name}: {e}"

            print(f"  ← Result: {result[:120]}")

            messages.append({
                "role": "tool",
                "content": result,
            })

    return "I wasn't able to complete that request — too many steps required."


# ── Interactive terminal mode ─────────────────────────────────────────────────
# Run directly to chat with Home Assistant from the terminal:
#   python ha_agent.py

async def _main():
    print(f"\nHome Assistant Agent — {OLLAMA_MODEL}")
    await load_context()
    print("\nType a command or question. Press Ctrl+C or type 'exit' to quit.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "bye"):
            print("Bye!")
            break

        print("Thinking...")
        reply = await run(user_input)
        print(f"\nBot: {reply}\n")


if __name__ == "__main__":
    asyncio.run(_main())
