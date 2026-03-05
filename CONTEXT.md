# Project Context: ha-telegram-bot

## Purpose
Control Home Assistant with natural language via Telegram, using a local AI (Ollama)
as the brain. You send a message, the AI interprets it, and Home Assistant acts on it.

## Home Assistant Setup
- URL: http://192.168.0.51:8123
- Version: 2026.3.0
- MCP Server: Enabled (Settings → Integrations → Model Context Protocol)
- MCP Endpoint: http://192.168.0.51:8123/mcp_server/sse

## Key Files

| File | Purpose |
|---|---|
| `bot.py` | Main entry point. Starts the Telegram bot and routes messages. |
| `ai_agent.py` | Connects to Ollama. Sends user messages + HA tools. Handles tool call loop. |
| `ha_mcp_client.py` | Connects to HA MCP server. Fetches tools and executes tool calls. |
| `.env` | Secret tokens (never committed to git). |
| `.env.example` | Template showing which variables are needed. |
| `requirements.txt` | Python dependencies. |

## Main Libraries & Why

| Library | Why this one |
|---|---|
| `python-telegram-bot` | Most mature Python Telegram library, good async support |
| `mcp` | Anthropic's official Python MCP SDK — connects to the HA MCP server |
| `ollama` | Official Python client for the local Ollama server |
| `python-dotenv` | Standard way to load secrets from a .env file |

## How the AI Tool Call Loop Works
1. User message arrives via Telegram
2. Python fetches available tools from HA MCP server
3. Message + tools are sent to Ollama
4. Ollama responds with a tool call (e.g., `turn_on light.kitchen`)
5. Python executes that tool via the MCP client
6. Result is sent back to Ollama
7. Steps 4–6 repeat until Ollama gives a plain text answer
8. That answer is sent back to the user on Telegram

## Security
- Telegram bot only responds to user IDs listed in `TELEGRAM_ALLOWED_USER_IDS`
- HA token stored in .env, never in code
- HA MCP server only accessible on local network

## Key Decisions
- Using MCP instead of direct REST API so the AI can discover HA tools automatically
- Using Ollama (local) instead of Claude API to keep everything on-device and free
- Model: llama3.2 (supports tool calling, runs well on Apple Silicon)
