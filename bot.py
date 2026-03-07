"""
bot.py

The Telegram bot — the entry point for the whole project.

When you send a message to your bot on Telegram, this file receives it,
passes it through the AI agent, and sends the reply back to you.

Security: only Telegram user IDs listed in TELEGRAM_ALLOWED_USER_IDS
can interact with the bot. Anyone else gets silently ignored.

Run with:
    python bot.py
"""

import logging
import os

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from ha_agent import load_context, run as agent_run

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_USER_IDS = {
    int(uid.strip())
    for uid in os.getenv("TELEGRAM_ALLOWED_USER_IDS", "").split(",")
    if uid.strip()
}

# Set up logging so you can see what the bot is doing in the terminal.
# This is very useful for debugging — you'll see every message received.
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
)
log = logging.getLogger(__name__)


def is_allowed(update: Update) -> bool:
    """Return True if the message sender is in the allowlist."""
    return update.effective_user.id in ALLOWED_USER_IDS


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle any plain text message by running it through the AI agent."""
    if not is_allowed(update):
        log.warning("Blocked message from user %s", update.effective_user.id)
        return

    user_text = update.message.text
    user_name = update.effective_user.first_name
    log.info("Message from %s (%s): %s", user_name, update.effective_user.id, user_text)

    # Show a "typing..." indicator while the agent is working.
    # This gives the user feedback that something is happening.
    await update.message.chat.send_action("typing")

    try:
        reply = await agent_run(user_text)
    except Exception as e:
        log.error("Agent error: %s", e)
        reply = "Sorry, something went wrong. Please try again."

    await update.message.reply_text(reply)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command."""
    if not is_allowed(update):
        return
    await update.message.reply_text(
        "Hi! I'm your Home Assistant bot.\n"
        "Send me a command like:\n"
        "• 'Turn off the living room lights'\n"
        "• 'What's the temperature in the bedroom?'\n"
        "• 'List all my lights'\n\n"
        "Type /help for more examples."
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /help command."""
    if not is_allowed(update):
        return
    await update.message.reply_text(
        "You can talk to me naturally. Here are some examples:\n\n"
        "*Lights*\n"
        "• Turn on the kitchen light\n"
        "• Set the bedroom light to 50% brightness\n"
        "• Turn off all lights\n\n"
        "*Status*\n"
        "• What lights are on?\n"
        "• What's the temperature in the living room?\n"
        "• Show me all my areas\n\n"
        "*Other*\n"
        "• Run the 'Good morning' automation\n"
        "• What devices are in the kitchen?\n",
        parse_mode="Markdown",
    )


def main() -> None:
    """Start the bot."""
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set in .env")
    if not ALLOWED_USER_IDS:
        raise ValueError("TELEGRAM_ALLOWED_USER_IDS is not set in .env")

    log.info("Starting bot... Allowed users: %s", ALLOWED_USER_IDS)

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Register command handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))

    # Register a handler for all plain text messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Load HA entity context once at startup so the model knows all entity IDs.
    import asyncio
    asyncio.get_event_loop().run_until_complete(load_context())

    log.info("Bot is running. Press Ctrl+C to stop.")
    app.run_polling()


if __name__ == "__main__":
    main()
