import re

from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler, MessageHandler, filters,
)

from bot import config
from bot.context.filters import RoomsFilter, DistrictFilter, ResidentialComplexFilter, PriceFilter, LivingAreaFilter
from bot.context.manager import Manager
from bot.log import logging
from bot.models import Apartments, Houses
from bot.navigation import main_menu_buttons, START_ROUTES, APARTMENTS_STATE, HOUSES_STATE, \
    END_ROUTES, APARTMENTS, WELCOME_TEXT, HOUSES

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


async def send_start_message(update: Update):
    reply_markup = await main_menu_buttons()
    if update.message:
        await update.message.reply_text(WELCOME_TEXT, reply_markup=reply_markup)
    elif update:
        await update.callback_query.edit_message_text(text=WELCOME_TEXT, reply_markup=reply_markup)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    logger.info("User %s started the conversation.", user.first_name)

    await send_start_message(update)

    return START_ROUTES


async def apartments(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show new choice of buttons"""

    m = Manager(
        model=Apartments,
        filters=[
            DistrictFilter,
            ResidentialComplexFilter,
            RoomsFilter,
            PriceFilter,
        ],
        update=update,
        context=context,
    )

    continue_flow = await m.process_action()

    if continue_flow:
        return APARTMENTS

    await send_start_message(update)
    return START_ROUTES


async def houses(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    m = Manager(
        model=Houses,
        filters=[
            DistrictFilter,
            RoomsFilter,
            LivingAreaFilter,
            PriceFilter,
        ],
        update=update,
        context=context,
    )

    continue_flow = await m.process_action()

    if continue_flow:
        return HOUSES

    await send_start_message(update)
    return START_ROUTES


async def subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    pass


async def end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Returns `ConversationHandler.END`, which tells the
    ConversationHandler that the conversation is over.
    """
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text="See you next time!")
    return ConversationHandler.END


def main() -> None:
    application = Application.builder().token(config.TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            START_ROUTES: [
                CallbackQueryHandler(apartments, pattern="^" + str(APARTMENTS_STATE) + "$"),
                CallbackQueryHandler(houses, pattern="^" + str(HOUSES_STATE) + "$"),
            ],
            APARTMENTS: [
                CallbackQueryHandler(apartments),
                MessageHandler(filters.Regex(re.compile(r'[0-9]+', re.IGNORECASE)), apartments),
            ],
            HOUSES: [
                CallbackQueryHandler(houses),
                MessageHandler(filters.Regex(re.compile(r'[0-9]+', re.IGNORECASE)), houses),

            ],
            END_ROUTES: [
                CallbackQueryHandler(end, pattern="^" + str(HOUSES_STATE) + "$"),
            ],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    application.add_handler(conv_handler)

    application.run_polling()


if __name__ == "__main__":
    main()
