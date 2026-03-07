# Project Context: ha-telegram-bot

## Purpose
Control Home Assistant with natural language via Telegram, using a local AI (Ollama)
as the brain. You send a message, the AI interprets it, and Home Assistant acts on it.

## Home Assistant Setup
- Local URL: http://192.168.0.51:8123
- Version: 2026.3.0
- MCP Server: Built-in HA MCP server (Streamable HTTP transport, port 9583)
- MCP URL: stored in `.env` as `HA_MCP_URL` (contains auth token in path)

## Key Files

| File | Purpose |
|---|---|
| `bot.py` | Main entry point. Starts the Telegram bot and routes messages. |
| `ai_agent.py` | Connects to Ollama. Sends user messages + HA tools. Handles tool call loop. |
| `ha_mcp_client.py` | Launches the ha-mcp subprocess and communicates via stdio MCP protocol. |
| `.env` | Secret tokens (never committed to git). |
| `.env.example` | Template showing which variables are needed. |
| `requirements.txt` | Python dependencies. |

## Main Libraries & Why

| Library | Why this one |
|---|---|
| `python-telegram-bot` | Most mature Python Telegram library, good async support |
| `mcp` | Anthropic's official Python MCP SDK — handles the stdio MCP protocol |
| `ollama` | Official Python client for the local Ollama server |
| `python-dotenv` | Standard way to load secrets from a .env file |

## How the HA MCP Server Works
HA's built-in MCP server runs on port 9583 and uses the Streamable HTTP transport.
Authentication is via a private token embedded in the URL (no Authorization header).
It exposes 89 tools covering entities, automations, dashboards, history, and more.
The connection is a direct HTTP call — no subprocess, no startup overhead.

## How the AI Tool Call Loop Works
1. User message arrives via Telegram
2. Python launches ha-mcp subprocess and fetches all 89 available tools
3. Message + tools are sent to Ollama
4. Ollama responds with a tool call (e.g., `ha_call_service` with light.turn_on)
5. Python executes that tool via the MCP client (which calls HA via Nabu Casa)
6. Result is sent back to Ollama
7. Steps 4–6 repeat until Ollama gives a plain text answer
8. That answer is sent back to the user on Telegram

## Security
- Telegram bot only responds to user IDs listed in `TELEGRAM_ALLOWED_USER_IDS`
- HA token stored in .env, never in code
- Bot connects to HA via Nabu Casa (works from any network)

## Key Decisions
- Using the built-in HA MCP server (Streamable HTTP) over the ha-mcp community
  package — faster (no subprocess), same 89 tools, simpler architecture
- Using Ollama (local) instead of Claude API to keep everything on-device and free
- Model: qwen3.5:9b (supports tool calling, 256K context, runs well on Apple Silicon)
- Streamable HTTP MCP transport: direct HTTP connection, no subprocess to manage
