"""
ha_mcp_client.py

Connects to Home Assistant via the ha-mcp community package.

How this works:
  Instead of connecting to a running server, we launch the `ha-mcp` tool
  as a subprocess and communicate with it over stdin/stdout. This is called
  a "stdio MCP server" — the process starts, we exchange messages, and it
  exits when we're done. The ha-mcp package handles all HA communication
  internally using your Nabu Casa URL and token.

  ha-mcp docs: https://github.com/vocoode/ha-mcp
"""

import asyncio
import os

from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

load_dotenv()

HOMEASSISTANT_URL = os.getenv("HOMEASSISTANT_URL")
HOMEASSISTANT_TOKEN = os.getenv("HOMEASSISTANT_TOKEN")

# These are the parameters needed to launch the ha-mcp subprocess.
# uvx downloads and runs ha-mcp@latest automatically — no manual install needed.
_SERVER_PARAMS = StdioServerParameters(
    command="uvx",
    args=["ha-mcp@latest"],
    env={
        "HOMEASSISTANT_URL": HOMEASSISTANT_URL,
        "HOMEASSISTANT_TOKEN": HOMEASSISTANT_TOKEN,
    },
)


async def get_tools() -> list[dict]:
    """
    Launch the ha-mcp subprocess, ask it what tools are available,
    and return them in the format Ollama expects (OpenAI-compatible).

    Each tool looks like:
    {
        "type": "function",
        "function": {
            "name": "HassTurnOn",
            "description": "Turn on a device or entity",
            "parameters": { ...JSON schema... }
        }
    }
    """
    async with stdio_client(_SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.list_tools()

            # Convert MCP tool format → Ollama tool format
            ollama_tools = []
            for tool in result.tools:
                ollama_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description or "",
                        "parameters": tool.inputSchema,
                    },
                })

            return ollama_tools


async def call_tool(tool_name: str, arguments: dict) -> str:
    """
    Launch the ha-mcp subprocess, execute a specific tool, and return
    the result as a plain string.

    tool_name  — the name of the tool, e.g. "HassTurnOn"
    arguments  — a dict of parameters, e.g. {"name": "kitchen light"}
    """
    async with stdio_client(_SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)

            # The result contains a list of content blocks (text, images, etc.)
            # We only care about text content here.
            text_parts = []
            for content in result.content:
                if hasattr(content, "text"):
                    text_parts.append(content.text)

            return "\n".join(text_parts) if text_parts else "Done."


# ── Quick test ────────────────────────────────────────────────────────────────
# Run this file directly to verify the connection works:
#   python ha_mcp_client.py

async def _main():
    print("Launching ha-mcp and connecting to Home Assistant...")
    print(f"HA URL: {HOMEASSISTANT_URL}\n")

    tools = await get_tools()
    print(f"Found {len(tools)} tools:\n")
    for tool in tools:
        fn = tool["function"]
        print(f"  • {fn['name']}")
        print(f"    {fn['description'][:80]}")
    print()


if __name__ == "__main__":
    asyncio.run(_main())
