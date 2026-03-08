# Home Assistant Telegram Bot

Control your Home Assistant with natural language via Telegram, powered by a local AI running entirely on your own machine — no cloud AI services required.

```
You (Telegram) → Bot → Ollama (local AI) → Home Assistant MCP → Your smart home
```

Ask things like:
- *"Are the office lights on?"*
- *"What's the temperature upstairs?"*
- *"Turn on the kitchen island light"*
- *"Which lights are currently on?"*

---

## Requirements

| Requirement | Notes |
|---|---|
| **Home Assistant** | 2024.11 or newer with MCP Server integration enabled |
| **Ollama** | Running locally — [ollama.com](https://ollama.com) |
| **Python 3.12+** | Install via Homebrew: `brew install python@3.12` |
| **Telegram bot** | Create via [@BotFather](https://t.me/BotFather) |

> **HA MCP URL:** Go to Settings → Integrations → Model Context Protocol in Home Assistant. The URL shown there is what goes in your `.env`.

---

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/your-username/ha-telegram-bot.git
cd ha-telegram-bot
```

### 2. Create a virtual environment and install dependencies

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure your environment

```bash
cp .env.example .env
```

Open `.env` and fill in your values:

```env
HA_MCP_URL=http://192.168.x.x:9583/private_your_token_here
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_ALLOWED_USER_IDS=your_numeric_telegram_user_id
OLLAMA_MODEL=qwen3.5:9b
```

> **Find your Telegram user ID:** Message [@userinfobot](https://t.me/userinfobot) on Telegram.

### 4. Pull the AI model

```bash
ollama pull qwen3.5:9b
```

---

## Running

### Terminal chat (no Telegram needed)

Great for testing and development:

```bash
source .venv/bin/activate
python src/ha_agent.py
```

```
You: are the office lights on?
🧠 Thinking: I need to search for office light entities...
  → Calling tool: ha_search_entities(...)
Bot: Both office lights are currently unavailable since March 7th.
```

### Telegram bot

```bash
source .venv/bin/activate
python src/bot.py
```

Send a message to your bot on Telegram to start controlling your home.

Press `Ctrl+C` to stop. If the bot is stuck in the background:
```bash
pkill -f "python src/bot.py"
```

---

## Project Structure

```
ha-telegram-bot/
├── src/
│   ├── bot.py            # Telegram bot — entry point for phone control
│   ├── ha_agent.py       # Smart HA agent with entity context + focused tools
│   ├── ai_agent.py       # Generic agent (used for experimentation)
│   └── ha_mcp_client.py  # Connects to Home Assistant via MCP protocol
├── docs/
│   ├── PLAN.md           # Implementation plan and progress
│   └── CONTEXT.md        # Architecture decisions and project context
├── .env.example          # Template — copy to .env and fill in your values
├── requirements.txt      # Python dependencies
└── README.md
```

---

## How It Works

1. Your message arrives via Telegram (or terminal)
2. The agent fetches your HA entity list (lights, switches, climate, etc.)
3. Your message + entity list + tools are sent to Ollama
4. Ollama decides which tool to call (e.g. `ha_get_state`, `ha_call_service`)
5. The tool is executed against your Home Assistant via the MCP protocol
6. Ollama gets the result and writes a plain-language reply
7. The reply is sent back to you

The model's reasoning is shown in the terminal via `🧠 Thinking:` lines so you can see exactly why it made each decision.

---

## Configuration

All settings live in `.env` (never committed to git):

| Variable | Description |
|---|---|
| `HA_MCP_URL` | Your HA MCP server URL (from HA Settings → Integrations → MCP) |
| `TELEGRAM_BOT_TOKEN` | Token from @BotFather |
| `TELEGRAM_ALLOWED_USER_IDS` | Comma-separated Telegram user IDs allowed to use the bot |
| `OLLAMA_MODEL` | Ollama model to use (default: `qwen3.5:9b`) |

---

## Troubleshooting

**Bot says it can't control devices**
The agent is in read-only mode by default while testing. To enable control, add `ha_call_service` and `ha_bulk_control` back to `ALLOWED_TOOLS` in `src/ha_agent.py`.

**`Conflict: terminated by other getUpdates request`**
Another bot instance is running. Stop it:
```bash
pkill -f "python src/bot.py"
```

**Ollama not responding**
Make sure Ollama is running — open the Ollama app or run `ollama serve`.

**HA MCP connection fails**
Check that `HA_MCP_URL` in `.env` is correct and that Home Assistant is reachable on your network.
