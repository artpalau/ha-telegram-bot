"""
ha_mcp_client.py

Connects to the Home Assistant built-in MCP server using the Streamable HTTP
transport. This is much faster than the subprocess approach — it's a direct
HTTP connection with no startup overhead.

The private URL contains the auth token, so no separate Authorization header
is needed. The URL is stored in .env as HA_MCP_URL.
"""

import asyncio
import os

from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

load_dotenv()

HA_MCP_URL = os.getenv("HA_MCP_URL")


async def get_tools() -> list[dict]:
    """
    Connect to the HA MCP server and return all available tools
    in the format Ollama expects (OpenAI-compatible tool spec).
    """
    async with streamablehttp_client(url=HA_MCP_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.list_tools()

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
    Connect to the HA MCP server, execute a tool, and return the result
    as a plain string.
    """
    async with streamablehttp_client(url=HA_MCP_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)

            text_parts = []
            for content in result.content:
                if hasattr(content, "text"):
                    text_parts.append(content.text)

            return "\n".join(text_parts) if text_parts else "Done."


# ── Quick test ────────────────────────────────────────────────────────────────
# Run this file directly to verify the connection works:
#   python ha_mcp_client.py

async def _main():
    print("Connecting to HA MCP server...")
    tools = await get_tools()
    print(f"Found {len(tools)} tools:\n")
    for tool in tools:
        fn = tool["function"]
        print(f"  • {fn['name']}")
        print(f"    {fn['description'][:80]}")


if __name__ == "__main__":
    asyncio.run(_main())
