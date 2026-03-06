# Home Assistant Telegram Bot

Control your Home Assistant with natural language via Telegram, powered by a local AI (Ollama + qwen3.5:9b).

## How It Works

```
You (Telegram) → Bot → Ollama AI → ha-mcp → Home Assistant (via Nabu Casa)
```

---

## Starting Everything

### 1. Start Ollama

Ollama must be running before the bot starts. Open a terminal and run:

```bash
ollama serve
```

Or simply open the **Ollama** app from your Applications folder — it runs in the menu bar.

Verify it's running:
```bash
ollama ps
```

### 2. Start the Bot

Open a terminal, navigate to the project folder, and run:

```bash
cd ~/Documents/Projects/ha-telegram-bot
source .venv/bin/activate
python bot.py
```

You should see:
```
[INFO] Starting bot... Allowed users: {your_id}
[INFO] Bot is running. Press Ctrl+C to stop.
```

The bot is now live. Send it a message on Telegram to test.

### 3. Stop the Bot

Press `Ctrl+C` in the terminal where the bot is running.

If the bot is running in the background and you need to force-stop it:
```bash
pkill -f "python bot.py"
```

---

## Configuration

All secrets and settings are in `.env` (never committed to git):

| Variable | Description |
|---|---|
| `HOMEASSISTANT_URL` | Your Nabu Casa URL |
| `HOMEASSISTANT_TOKEN` | HA Long-Lived Access Token |
| `TELEGRAM_BOT_TOKEN` | Token from @BotFather |
| `TELEGRAM_ALLOWED_USER_IDS` | Your Telegram user ID (only you can use the bot) |
| `OLLAMA_MODEL` | AI model to use (default: `qwen3.5:9b`) |

---

## Project Structure

| File | Purpose |
|---|---|
| `bot.py` | Telegram bot — entry point, run this to start |
| `ai_agent.py` | AI brain — sends messages to Ollama, handles tool call loop |
| `ha_mcp_client.py` | HA connection — launches ha-mcp and executes tools |
| `.env` | Your secrets (not in git) |
| `.env.example` | Template for .env |

---

## Troubleshooting

**Bot says "I don't have access to turn off lights"**
The AI model needs better guidance to use the `ha_call_service` tool. This is a known issue — the system prompt in `ai_agent.py` needs tuning. See `PLAN.md` for what's next.

**`Conflict: terminated by other getUpdates request`**
Another bot instance is already running. Stop it with:
```bash
pkill -f "python bot.py"
```

**Ollama not responding**
Make sure Ollama is running (`ollama serve` or open the app), then restart the bot.

**ha-mcp connection fails**
Check that your `HOMEASSISTANT_TOKEN` in `.env` is valid and not expired. Regenerate it at:
`your-ha-instance/profile` → Long-Lived Access Tokens

---

## Dependencies

- Python 3.12 (installed via Homebrew)
- Ollama with `qwen3.5:9b` model
- `uvx` (comes with `uv`, installed via Homebrew)

Install Python dependencies:
```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
