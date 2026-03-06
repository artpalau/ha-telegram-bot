# Project Context: ha-telegram-bot

## Purpose
Control Home Assistant with natural language via Telegram, using a local AI (Ollama)
as the brain. You send a message, the AI interprets it, and Home Assistant acts on it.

## Home Assistant Setup
- Local URL: http://192.168.0.51:8123
- Remote URL: Nabu Casa cloud (used by the bot for connectivity from anywhere)
- Version: 2026.3.0
- MCP Package: `ha-mcp` (community package, run via `uvx ha-mcp@latest`)

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

## How ha-mcp Works
`ha-mcp` is a community MCP server that wraps the HA WebSocket API. Instead of
connecting to a running server, we launch it as a subprocess with `uvx ha-mcp@latest`
and communicate via stdin/stdout (stdio transport). It exposes 89 tools covering
entities, automations, dashboards, history, and more.

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
- Using `ha-mcp` (community package via uvx) instead of the built-in HA MCP server —
  it exposes far more tools (89 vs a handful) and works via Nabu Casa cloud URL
- Using Ollama (local) instead of Claude API to keep everything on-device and free
- Model: llama3.2 (supports tool calling, runs well on Apple Silicon)
- stdio MCP transport: ha-mcp runs as a subprocess, no server to manage
