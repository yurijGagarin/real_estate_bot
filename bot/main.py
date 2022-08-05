import json
from json import JSONDecodeError
from pprint import pprint

import telegram.error
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
)

from bot import config
from bot.context import Manager, State
from bot.filters import RoomsBaseFilter, DistrictBaseFilter, ResidentialComplexBaseFilter
from bot.log import logging
from bot.models import Apartments

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Stages
# TODO use string consts instread of numbers
START_ROUTES, APARTMENTS, HOUSES, END_ROUTES = range(4)
# Callback data
APARTMENTS_STATE = 'APARTMENTS_STATE'
HOUSES_STATE = 'HOUSES_STATE'

# TODO use string consts instread of numbers
THREE, FOUR = range(2)
ONE_ONE, ONE_TWO, ONE_THREE, ONE_FOUR = range(11, 15)

# Main Menu Buttons
START_BUTTONS = {
    'Оренда Квартир': APARTMENTS_STATE,
    'Орена Домів': HOUSES_STATE,
    'Повідомлення про нові оголошення': THREE,
}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Send message on `/start`."""
    # Get user that sent /start and log his name
    user = update.message.from_user
    logger.info("User %s started the conversation.", user.first_name)
    # Build InlineKeyboard where each button has a displayed text
    # and a string as callback_data
    # The keyboard is a list of button rows, where each row is in turn
    # a list (hence `[[...]]`).
    keyboard = [[]]
    for k, v in START_BUTTONS.items():
        keyboard[0].append(

            InlineKeyboardButton(k, callback_data=str(v)),

        )
    reply_markup = InlineKeyboardMarkup(keyboard)
    # Send message with text and appended InlineKeyboard
    await update.message.reply_text("Оберіть бажану послугу", reply_markup=reply_markup)
    # Tell ConversationHandler that we're in state `FIRST` now

    return START_ROUTES


async def start_over(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Prompt same text & keyboard as `start` does but not as new message"""
    # Get CallbackQuery from Update
    query = update.callback_query
    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    await query.answer()
    keyboard = [
        [
            InlineKeyboardButton("1", callback_data=str(APARTMENTS_STATE)),
            InlineKeyboardButton("2", callback_data=str(HOUSES_STATE)),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    # Instead of sending a new message, edit the message that
    # originated the CallbackQuery. This gives the feeling of an
    # interactive menu.
    await query.edit_message_text(text="Start handler, Choose a route", reply_markup=reply_markup)
    return START_ROUTES


async def apartments(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show new choice of buttons"""

    m = Manager(
        model=Apartments,
        filters=[
            DistrictBaseFilter,
            ResidentialComplexBaseFilter,
            RoomsBaseFilter,
        ],
        update=update,
        context=context,
    )

    await m.process_action()

    return APARTMENTS


async def houses(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show new choice of buttons"""
    query = update.callback_query
    await query.answer()
    keyboard = [
        [
            InlineKeyboardButton("1", callback_data=str(APARTMENTS_STATE)),
            InlineKeyboardButton("3", callback_data=str(THREE)),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text="Second CallbackQueryHandler, Choose a route", reply_markup=reply_markup
    )
    return START_ROUTES


async def subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show new choice of buttons. This is the end point of the conversation."""
    query = update.callback_query
    await query.answer()
    keyboard = [
        [
            InlineKeyboardButton("Yes, let's do it again!", callback_data=str(APARTMENTS_STATE)),
            InlineKeyboardButton("Nah, I've had enough ...", callback_data=str(HOUSES_STATE)),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text="Third CallbackQueryHandler. Do want to start over?", reply_markup=reply_markup
    )
    # Transfer to conversation state `SECOND`
    return END_ROUTES


async def end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Returns `ConversationHandler.END`, which tells the
    ConversationHandler that the conversation is over.
    """
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text="See you next time!")
    return ConversationHandler.END




def main() -> None:
    """Run the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(config.TOKEN).build()

    # Setup conversation handler with the states FIRST and SECOND
    # Use the pattern parameter to pass CallbackQueries with specific
    # data pattern to the corresponding handlers.
    # ^ means "start of line/string"
    # $ means "end of line/string"
    # So ^ABC$ will only allow 'ABC'
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            START_ROUTES: [
                CallbackQueryHandler(apartments, pattern="^" + str(APARTMENTS_STATE) + "$"),
                CallbackQueryHandler(houses, pattern="^" + str(HOUSES_STATE) + "$"),
                # CallbackQueryHandler(subscription, pattern="^" + str(THREE) + "$"),
                # CallbackQueryHandler(region, pattern="^" + str(ONE_ONE) + "$"),
            ],
            APARTMENTS: [
                CallbackQueryHandler(apartments),
            ],
            END_ROUTES: [
                CallbackQueryHandler(start_over, pattern="^" + str(APARTMENTS_STATE) + "$"),
                CallbackQueryHandler(end, pattern="^" + str(HOUSES_STATE) + "$"),
            ],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    # Add ConversationHandler to application that will be used for handling updates
    application.add_handler(conv_handler)

    # Run the bot until the user presses Ctrl-C
    application.run_polling()


if __name__ == "__main__":
    main()
