import logging

from telegram import *
from telegram.ext import *

import config

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.DEBUG if config.DEBUG else logging.INFO,
)


async def start(update: Update, context: CallbackContext):
    text = "hello"
    await context.bot.send_message(update.effective_user.id, text=text)


def main():
    logging.info("Starting...")
    application = ApplicationBuilder().token(config.TOKEN).build()

    application.add_handler(CommandHandler("start", start))

    application.run_polling()


if __name__ == "__main__":
    main()
