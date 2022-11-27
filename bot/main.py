import asyncio
import re

import aioschedule as schedule
import sentry_sdk
from pyrogram import Client
from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters, ContextTypes,
)

from bot import config
from bot.ads.handlers import ads_dialog_handler
from bot.ads.navigation.constants import ADS_DIALOG_STAGE
from bot.context.filters import (
    RoomsFilter,
    DistrictFilter,
    ResidentialComplexFilter,
    PriceFilter,
    AdditionalFilter, )
from bot.context.message_forwarder import MessageForwarder
from bot.log import logging
from bot.models import Apartments, Houses
from bot.navigation.basic_keyboard_builder import show_menu
from bot.navigation.buttons_constants import START_BUTTONS
from bot.navigation.constants import (
    SUBSCRIPTION_STAGE,
    START_STAGE,
    ADMIN_MENU_STAGE,
    APARTMENTS_STAGE,
    HOUSES_STAGE,
    APARTMENTS_STATE,
    HOUSES_STATE,
    ADMIN_MENU_STATE,
    SUBSCRIPTION_STATE,
    REFRESH_DB_STATE,
    TOTAL_USERS_STATE,
    RECENT_HOUR_USERS_STATE,
    TOTAL_SUBSCRIBED_USERS_STATE,
    CANCEL_SUBSCRIPTION_STATE,
    MAIN_MENU_STATE, RENT_STAGE, RENT_STATE, ADS_STATE, ADS_STAGE, ADS_APS_STATE, HELP_STAGE, SUBMIT_HELP_STATE,
    SUBMIT_STATE, GEO_DATA_STAGE, CHECK_GEOLINK_STATE, MAIN_MENU_TEXT, )
from bot.stages.admin_stage import admin_menu, get_total_users, get_recent_hour_users, \
    get_total_users_with_subscription, check_geolink, submit_geolink, user_geolink, create_refresh_handler, sync_data
from bot.stages.ads_stage import ads_handler
from bot.stages.help_stage import help_message_handler, submit_help, help_ask
from bot.stages.rent_stage import create_filter_handler, rent_handler, subscription, cancel_subscription

logger = logging.getLogger(__name__)
sentry_sdk.init(dsn=config.SENTRY_DSN,
                traces_sample_rate=1.0,
                environment=config.SENTRY_ENV
                )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    user_logging = update.message.from_user
    logger.info("User %s started the conversation.", user_logging.first_name)
    await show_menu(update=update,
                    context=context,
                    buttons_pattern=START_BUTTONS,
                    text=MAIN_MENU_TEXT,
                    items_in_a_row=1,
                    main_menu=True)

    return START_STAGE


async def back_to_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    await show_menu(update=update,
                    context=context,
                    buttons_pattern=START_BUTTONS,
                    text=MAIN_MENU_TEXT,
                    items_in_a_row=1,
                    main_menu=True)

    return START_STAGE


def main() -> None:
    application = Application.builder().token(config.TOKEN).build()
    app = Client(
        name=config.SESSION_NAME,
        api_id=config.API_ID,
        api_hash=config.API_HASH,
        bot_token=config.TOKEN,
        no_updates=True,
    )
    app.start()
    forwarder = MessageForwarder(app=app, from_chat_id=config.FROM_CHAT_ID)

    FILTERS = {
        APARTMENTS_STAGE: {
            "model": Apartments,
            "filters": [
                AdditionalFilter,
                DistrictFilter,
                ResidentialComplexFilter,
                RoomsFilter,
                PriceFilter,
            ],
            "stage": APARTMENTS_STAGE,
        },
        HOUSES_STAGE: {
            "model": Houses,
            "filters": [
                DistrictFilter,
                RoomsFilter,
                PriceFilter,
            ],
            "stage": HOUSES_STAGE,
        },
    }

    apartments_handler = create_filter_handler(
        model=FILTERS[APARTMENTS_STAGE]["model"],
        filters=FILTERS[APARTMENTS_STAGE]["filters"],
        stage=FILTERS[APARTMENTS_STAGE]["stage"],
        forwarder=forwarder,
    )
    houses_handler = create_filter_handler(
        model=FILTERS[HOUSES_STAGE]["model"],
        filters=FILTERS[HOUSES_STAGE]["filters"],
        stage=FILTERS[HOUSES_STAGE]["stage"],
        forwarder=forwarder,
    )

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
        ],
        states={
            START_STAGE: [
                CallbackQueryHandler(
                    rent_handler, pattern="^" + str(RENT_STATE) + "$"
                ),
                CallbackQueryHandler(
                    ads_handler, pattern="^" + str(ADS_STATE) + "$"
                ),
                CallbackQueryHandler(
                    admin_menu, pattern="^" + str(ADMIN_MENU_STATE) + "$"
                ),
            ],
            RENT_STAGE: [
                CallbackQueryHandler(
                    apartments_handler, pattern="^" + str(APARTMENTS_STATE) + "$"
                ),
                CallbackQueryHandler(
                    houses_handler, pattern="^" + str(HOUSES_STATE) + "$"
                ),

                CallbackQueryHandler(
                    subscription, pattern="^" + str(SUBSCRIPTION_STATE) + "$"
                ),
                CallbackQueryHandler(
                    back_to_main_menu, pattern="^" + str(MAIN_MENU_STATE) + "$"
                ),
            ],
            ADS_STAGE: [
                CallbackQueryHandler(
                    ads_dialog_handler, pattern="^" + str(ADS_APS_STATE) + "$"
                ),
                CallbackQueryHandler(
                    back_to_main_menu, pattern="^" + str(MAIN_MENU_STATE) + "$"
                ),
            ],
            ADS_DIALOG_STAGE: {
                CallbackQueryHandler(
                    back_to_main_menu, pattern="^" + str(MAIN_MENU_STATE) + "$"
                ),
                CallbackQueryHandler(
                    ads_dialog_handler, pattern="^" + str(ADS_APS_STATE) + "$"),
                MessageHandler(
                    filters.TEXT,
                    ads_dialog_handler,
                ),
                CallbackQueryHandler(ads_dialog_handler),
                MessageHandler(filters.USER_ATTACHMENT, ads_dialog_handler),
                MessageHandler(filters.Document.IMAGE, ads_dialog_handler),
                MessageHandler(filters.PHOTO, ads_dialog_handler),
                MessageHandler(filters.CONTACT, ads_dialog_handler),
            },
            ADMIN_MENU_STAGE: [
                CallbackQueryHandler(
                    create_refresh_handler(forwarder=forwarder),
                    pattern="^" + str(REFRESH_DB_STATE) + "$",
                ),
                CallbackQueryHandler(
                    back_to_main_menu, pattern="^" + str(MAIN_MENU_STATE) + "$"
                ),
                CallbackQueryHandler(
                    get_total_users, pattern="^" + str(TOTAL_USERS_STATE) + "$"
                ),
                CallbackQueryHandler(
                    get_recent_hour_users,
                    pattern="^" + str(RECENT_HOUR_USERS_STATE) + "$",
                ),
                CallbackQueryHandler(
                    get_total_users_with_subscription,
                    pattern="^" + str(TOTAL_SUBSCRIBED_USERS_STATE) + "$",
                ),
                CallbackQueryHandler(
                    check_geolink,
                    pattern="^" + str(CHECK_GEOLINK_STATE) + "$",
                ),

            ],
            GEO_DATA_STAGE: [
                CallbackQueryHandler(
                    submit_geolink,
                    pattern="^" + str(SUBMIT_STATE) + "$",
                ),
                MessageHandler(
                    filters.TEXT & (~filters.COMMAND), user_geolink
                ),
                CallbackQueryHandler(
                    back_to_main_menu, pattern="^" + str(MAIN_MENU_STATE) + "$"
                ),
            ],
            APARTMENTS_STAGE: [
                CallbackQueryHandler(apartments_handler),
                MessageHandler(
                    filters.Regex(re.compile(r"[0-9]+", re.IGNORECASE)),
                    apartments_handler,
                ),
            ],
            HOUSES_STAGE: [
                CallbackQueryHandler(houses_handler),
                MessageHandler(
                    filters.Regex(re.compile(r"[0-9]+", re.IGNORECASE)), houses_handler
                ),
            ],
            SUBSCRIPTION_STAGE: [
                CallbackQueryHandler(
                    apartments_handler, pattern="^" + str(APARTMENTS_STATE) + "$"
                ),
                CallbackQueryHandler(
                    houses_handler, pattern="^" + str(HOUSES_STATE) + "$"
                ),
                CallbackQueryHandler(
                    cancel_subscription,
                    pattern="^" + str(CANCEL_SUBSCRIPTION_STATE) + "$",
                ),
                CallbackQueryHandler(
                    rent_handler, pattern="^" + str(MAIN_MENU_STATE) + "$"
                ),
            ],
            HELP_STAGE: [
                MessageHandler(
                    filters.TEXT & (~filters.COMMAND), help_message_handler
                ),
                CallbackQueryHandler(
                    back_to_main_menu, pattern="^" + str(MAIN_MENU_STATE) + "$"
                ),
                CallbackQueryHandler(
                    submit_help, pattern="^" + str(SUBMIT_HELP_STATE) + "$"
                ),
            ]
        },
        fallbacks=[
            CommandHandler("start", start),
            CommandHandler("help", help_ask)
        ],
    )

    application.add_handler(conv_handler)
    loop = asyncio.get_event_loop()

    loop.create_task(start_schedules(forwarder))
    application.run_polling()
    app.stop()


async def start_schedules(forwarder: MessageForwarder):
    schedule.every(2).hours.do(sync_data, forwarder=forwarder)

    while True:
        await asyncio.sleep(360)
        await schedule.run_pending()


if __name__ == "__main__":
    main()
