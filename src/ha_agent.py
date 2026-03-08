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
    "ha_get_overview",      # general home status summary
    "ha_get_history",       # was a device on/off at a certain time?
    "ha_list_services",     # discover what services a domain supports
}
# READ-ONLY MODE: ha_call_service and ha_bulk_control are intentionally excluded.
# Re-add them here once testing is complete and you're happy with the agent.

# This gets populated by load_context() at startup.
# It holds a human-readable map of your devices (name → entity_id).
_entity_context = ""

# Base system prompt — entity context gets appended to this at startup.
_BASE_PROMPT = """You are a Home Assistant assistant in READ-ONLY mode.
You can query and report on the smart home but you cannot change anything.

RULES — follow these exactly:
- ALWAYS use tools. Never say you "can't" or "don't have access" — you do.
- READ-ONLY: do not attempt to turn devices on/off or change any settings.
  If asked to control something, explain that you are in read-only mode.
- To find devices: use ha_search_entities.
- To check a device state: use ha_get_state with the entity_id.
- To get a home overview: use ha_get_overview.
- Be concise: report what you found in a few sentences.
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


async def run(user_message: str, show_thinking: bool = False) -> str:
    """
    Process a user's message and return the AI's final reply.
    Call load_context() at least once before calling this.

    show_thinking — if True, prints the model's chain-of-thought reasoning
                    to the terminal (never included in the returned reply).
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
            think=True,   # asks qwen3.5 to output its reasoning before answering
        )

        assistant_message = response.message

        # Print the model's thinking if available and requested.
        # This is purely for terminal debugging — it never reaches Telegram.
        if show_thinking and getattr(assistant_message, "thinking", None):
            print(f"\n🧠 Thinking: {assistant_message.thinking}\n")

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
            user_input = (await asyncio.to_thread(input, "You: ")).strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "bye"):
            print("Bye!")
            break

        print("Thinking...")
        reply = await run(user_input, show_thinking=True)
        print(f"\nBot: {reply}\n")


if __name__ == "__main__":
    asyncio.run(_main())
