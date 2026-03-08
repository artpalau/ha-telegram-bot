"""
ai_agent.py

The AI brain of the bot. Takes a user's natural language message,
gives Ollama the list of available Home Assistant tools, and runs a
"tool call loop" until Ollama produces a final text reply.

How the tool call loop works:
  1. Send the user's message + all HA tools to Ollama
  2. Ollama replies with either:
     a) A tool call  → we execute it via ha_mcp_client, send the result
        back to Ollama, and go to step 2 again
     b) A plain text answer → we return it to the caller (the Telegram bot)

This loop is what makes the bot feel "intelligent" — Ollama can chain
multiple tool calls together to answer complex questions like
"turn off all lights except the bedroom".
"""

import asyncio
import os

import ollama
from dotenv import load_dotenv

from ha_mcp_client import call_tool, get_tools

load_dotenv()

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3.5:9b")

# This is the system prompt — it tells the model what its job is and
# how to behave. A clear system prompt makes responses much more consistent.
SYSTEM_PROMPT = """You are a Home Assistant controller with full access to the user's smart home.
You have tools to control and query EVERYTHING in Home Assistant.

IMPORTANT RULES:
- ALWAYS use tools to answer questions or carry out commands. Never say you "don't have access" — you do.
- To find lights, switches, sensors or any device: use ha_search_entities or ha_get_overview.
- To turn devices on/off or change settings: use ha_call_service.
- To get the current state of a device: use ha_get_state or ha_get_states.
- If one tool doesn't return what you need, try another. Never give up without trying at least one tool.
- Be concise: confirm success in one sentence, or report what you found briefly."""


async def run(user_message: str) -> str:
    """
    Process a user's message and return the AI's final text reply.

    This is the main function called by the Telegram bot.
    """
    # Step 1: Get the current list of available HA tools.
    # We fetch these fresh each time so new devices are always available.
    tools = await get_tools()

    # Step 2: Build the conversation. We start with the system prompt
    # (the AI's instructions) and the user's message.
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    # Step 3: Run the tool call loop.
    # We keep going until Ollama gives us a plain text reply with no tool calls.
    MAX_ITERATIONS = 10  # safety limit to prevent infinite loops
    for _ in range(MAX_ITERATIONS):
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=messages,
            tools=tools,
        )

        assistant_message = response.message

        # Add Ollama's response to the conversation history so it has context
        # for its next reply.
        messages.append(assistant_message)

        # If there are no tool calls, Ollama is done — return the text reply.
        if not assistant_message.tool_calls:
            return assistant_message.content or "Done."

        # There are tool calls — execute each one and add the results.
        for tool_call in assistant_message.tool_calls:
            tool_name = tool_call.function.name
            tool_args = tool_call.function.arguments or {}

            print(f"  → Calling tool: {tool_name}({tool_args})")

            try:
                result = await call_tool(tool_name, tool_args)
            except Exception as e:
                result = f"Error calling {tool_name}: {e}"

            print(f"  ← Result: {result[:100]}")

            # Add the tool result to the conversation so Ollama can see
            # what happened and decide what to do next.
            messages.append({
                "role": "tool",
                "content": result,
            })

    return "I wasn't able to complete that request — too many steps required."


# ── Interactive terminal mode ─────────────────────────────────────────────────
# Run this file directly to chat with your Home Assistant from the terminal:
#   python ai_agent.py
#
# Type any command and press Enter. Type 'exit' or press Ctrl+C to quit.

async def _main():
    print(f"\nHome Assistant AI — using {OLLAMA_MODEL}")
    print("Type a command or question. Press Ctrl+C or type 'exit' to quit.\n")

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
