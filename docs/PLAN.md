# Plan: Home Assistant Telegram Bot with Ollama + MCP

## Goal
A Telegram bot that lets you control Home Assistant using natural language.
You send a message like "turn off the living room lights" and the bot uses a local AI
(Ollama) to understand the intent, then executes it via the Home Assistant MCP server.

## Architecture Overview

```
You (Telegram app)
    ↓ natural language message
Telegram Bot (python-telegram-bot)
    ↓ forwards message
AI Agent (Ollama, running locally)
    ↓ picks the right tool to call
Python MCP Client (mcp library, stdio transport)
    ↓ stdin/stdout
ha-mcp subprocess (uvx ha-mcp@latest) — 89 tools
    ↓ WebSocket API over Nabu Casa
Home Assistant (2026.3.0)
    ↑ returns result
Telegram Bot → sends confirmation back to you
```

## Phases

---

### Phase 1: Project Setup
- [x] Create project folder
- [x] Create PLAN.md and CONTEXT.md
- [x] Initialize git + .gitignore
- [ ] Create Python virtual environment
- [ ] Install dependencies (see requirements.txt)
- [ ] Create .env file with secrets (HA token, Telegram token)

---

### Phase 2: Home Assistant MCP Connection ✅
**Goal:** Connect to HA via the ha-mcp community package and list available tools.

Files created:
- `ha_mcp_client.py` — launches ha-mcp subprocess, lists tools, executes tool calls

Steps completed:
1. Discovered the correct MCP setup: `ha-mcp` community package via `uvx`
2. Uses Nabu Casa cloud URL for connectivity (not local IP)
3. Uses stdio MCP transport (subprocess) instead of SSE
4. Connected successfully — 89 tools available

Milestone: ✅ Running `python ha_mcp_client.py` prints all 89 available HA tools.

---

### Phase 3: Ollama Integration
**Goal:** Have Ollama understand a natural language command and decide which MCP tool to call.

Files to create:
- `ai_agent.py` — sends user message + MCP tools to Ollama, handles tool call loop

Steps:
1. Install Ollama and pull a model that supports tool calling (recommended: `llama3.2`)
2. Connect to Ollama via its Python library
3. Pass the user's message + list of available HA tools to Ollama
4. Ollama replies with a tool call → execute it via MCP client
5. Send the result back to Ollama → it generates a friendly reply
6. Repeat until Ollama gives a final text answer (the "tool call loop")

Milestone: Running `python ai_agent.py "turn off the kitchen light"` executes in HA
           and prints a confirmation.

---

### Phase 4: Telegram Bot
**Goal:** Create a Telegram bot that receives messages and routes them through the AI agent.

Files to create:
- `bot.py` — main entry point, handles Telegram messages

Steps:
1. Create a bot via @BotFather on Telegram → get bot token
2. Use `python-telegram-bot` to receive messages
3. Route each message through the AI agent from Phase 3
4. Send the agent's reply back to the user
5. Add a user ID allowlist (so only you can use the bot)

Milestone: Sending a message in Telegram controls Home Assistant.

---

### Phase 5: Polish & Reliability
- Add a `/status` command that lists which devices are on/off
- Add a `/help` command explaining what you can ask
- Handle errors gracefully (HA offline, Ollama offline, unknown command)
- Add basic logging so you can debug issues
- Test with a variety of commands

---

## Dependencies
```
python-telegram-bot  # Telegram messaging
mcp                  # MCP protocol client (Anthropic's SDK)
ollama               # Python client for local Ollama
python-dotenv        # Load secrets from .env file
httpx                # HTTP client (used internally by mcp)
```

## Environment Variables (.env)
```
HOMEASSISTANT_URL=https://your-instance.ui.nabu.casa
HOMEASSISTANT_TOKEN=<long-lived access token from HA>
TELEGRAM_BOT_TOKEN=<token from @BotFather>
TELEGRAM_ALLOWED_USER_IDS=<your Telegram numeric user ID>
OLLAMA_MODEL=llama3.2
```

## Decisions Made
- **MCP over REST API:** The HA MCP server exposes tools that the AI can discover
  automatically, so we don't need to write custom API wrapper code.
- **Ollama over Claude API:** Keeps everything local and free. Claude API can be
  added later as a fallback or alternative.
- **llama3.2 model:** Supports tool calling (required for MCP bridge), runs well on
  Apple Silicon.
- **python-telegram-bot:** Most mature and well-documented Python Telegram library.
