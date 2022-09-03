import asyncio
import datetime
import re
from typing import Type, List

import aioschedule as schedule
import sentry_sdk
from pyrogram import Client
from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler, MessageHandler, filters,
)

from bot import config
from bot.context.filters import RoomsFilter, DistrictFilter, ResidentialComplexFilter, PriceFilter, BaseFilter, \
    AdditionalFilter
from bot.context.manager import Manager
from bot.context.message_forwarder import MessageForwarder
from bot.context.state import State
from bot.data_manager import DataManager
from bot.db import get_user, save_user, get_regular_users, get_recent_users, get_users_with_subscription
from bot.log import logging
from bot.models import Apartments, Houses, Ad
from bot.navigation import START_ROUTES, APARTMENTS_STATE, HOUSES_STATE, \
    APARTMENTS, HOUSES, REFRESH_DB, show_main_menu, SUBSCRIPTION, SUBSCRIPTION_STATE, \
    show_subscription_menu, CANCEL_SUBSCRIPTION, MAIN_MENU, ADMIN_MENU, ADMIN_MENU_CALLBACK, show_admin_menu, \
    TOTAL_USERS, RECENT_HOUR_USERS, TOTAL_SUBSCRIBED_USERS

logger = logging.getLogger(__name__)
sentry_sdk.init(
    dsn=config.SENTRY_DSN,
    traces_sample_rate=1.0
)


async def sync_data(forwarder: MessageForwarder):
    data_manager = DataManager()
    await data_manager.sync_data()
    await data_manager.notify_users(forwarder)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    user_logging = update.message.from_user
    logger.info("User %s started the conversation.", user_logging.first_name)

    await show_main_menu(update, context)

    return START_ROUTES


async def subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    state = State.from_context(context)
    state.is_subscription = True
    state.update_context(context)
    await show_subscription_menu(update)

    return SUBSCRIPTION


async def cancel_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    user = await get_user(update)
    user.subscription = None
    user.subscription_text = None
    await save_user(user)
    await show_subscription_menu(update)

    return SUBSCRIPTION


async def back_to_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    await show_main_menu(update, context)

    return START_ROUTES


async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    await show_admin_menu(update, context)

    return ADMIN_MENU


async def get_total_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = await get_regular_users()
    total_users = len(users)
    text = f'Всього користувачів: {total_users}'
    await show_admin_menu(update, context, text)
    return ADMIN_MENU


async def get_recent_hour_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    current_time = datetime.datetime.utcnow()
    last_hour = current_time - datetime.timedelta(hours=1)
    users = await get_recent_users(last_hour)
    total_users = len(users)
    text = f'Користувачів за останню годину: {total_users}'
    await show_admin_menu(update, context, text)
    return ADMIN_MENU


async def get_total_users_with_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = await get_users_with_subscription()
    total_users = len(users)
    text = f'Всього користувачів з підпискою: {total_users}'
    await show_admin_menu(update, context, text)
    return ADMIN_MENU


def create_refresh_handler(forwarder: MessageForwarder):
    async def refresh_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.info('success sync')
        await sync_data(forwarder=forwarder)
        text = 'База даних оновлена.\nГарного вам дня 😊'
        await show_admin_menu(update, context, text_outer=text)
        return ADMIN_MENU

    return refresh_handler


def create_filter_handler(model: Type[Ad], filters: List[Type[BaseFilter]], stage: str, forwarder: MessageForwarder):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        m = Manager(
            model=model,
            filters=filters,
            update=update,
            context=context,
            forwarder=forwarder,
        )

        is_subscription = m.state.is_subscription
        continue_flow = await m.process_action()

        if continue_flow:
            return stage

        if is_subscription:
            await show_subscription_menu(update)
            return SUBSCRIPTION

        await show_main_menu(update, context)
        return START_ROUTES

    return handler


def main() -> None:
    application = Application.builder().token(config.TOKEN).build()
    app = Client(name=config.SESSION_NAME,
                 api_id=config.API_ID, api_hash=config.API_HASH,
                 bot_token=config.TOKEN,
                 no_updates=True
                 )
    app.start()
    forwarder = MessageForwarder(app=app, from_chat_id=config.FROM_CHAT_ID)

    FILTERS = {
        APARTMENTS: {
            "model": Apartments,
            "filters": [
                AdditionalFilter,
                DistrictFilter,
                ResidentialComplexFilter,
                RoomsFilter,
                PriceFilter,

            ],
            "stage": APARTMENTS,
        },
        HOUSES: {
            "model": Houses,
            "filters": [
                DistrictFilter,
                RoomsFilter,
                PriceFilter,
            ],
            "stage": HOUSES,
        },
    }

    apartments_handler = create_filter_handler(
        model=FILTERS[APARTMENTS]["model"],
        filters=FILTERS[APARTMENTS]["filters"],
        stage=FILTERS[APARTMENTS]["stage"],
        forwarder=forwarder,

    )
    houses_handler = create_filter_handler(
        model=FILTERS[HOUSES]["model"],
        filters=FILTERS[HOUSES]["filters"],
        stage=FILTERS[HOUSES]["stage"],
        forwarder=forwarder,
    )

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),

        ],

        states={
            START_ROUTES: [
                CallbackQueryHandler(apartments_handler, pattern="^" + str(APARTMENTS_STATE) + "$"),
                CallbackQueryHandler(houses_handler, pattern="^" + str(HOUSES_STATE) + "$"),
                CallbackQueryHandler(admin_menu, pattern="^" + str(ADMIN_MENU_CALLBACK) + "$"),
                CallbackQueryHandler(subscription, pattern="^" + str(SUBSCRIPTION_STATE) + "$"),

            ],
            ADMIN_MENU: [
                CallbackQueryHandler(create_refresh_handler(forwarder=forwarder), pattern="^" + str(REFRESH_DB) + "$"),
                CallbackQueryHandler(back_to_main_menu, pattern="^" + str(MAIN_MENU) + "$"),
                CallbackQueryHandler(get_total_users, pattern="^" + str(TOTAL_USERS) + "$"),
                CallbackQueryHandler(get_recent_hour_users, pattern="^" + str(RECENT_HOUR_USERS) + "$"),
                CallbackQueryHandler(get_total_users_with_subscription,
                                     pattern="^" + str(TOTAL_SUBSCRIBED_USERS) + "$"),

            ],
            APARTMENTS: [
                CallbackQueryHandler(apartments_handler),
                MessageHandler(filters.Regex(re.compile(r'[0-9]+', re.IGNORECASE)), apartments_handler),
            ],
            HOUSES: [
                CallbackQueryHandler(houses_handler),
                MessageHandler(filters.Regex(re.compile(r'[0-9]+', re.IGNORECASE)), houses_handler),
            ],
            SUBSCRIPTION: [
                CallbackQueryHandler(apartments_handler, pattern="^" + str(APARTMENTS_STATE) + "$"),
                CallbackQueryHandler(houses_handler, pattern="^" + str(HOUSES_STATE) + "$"),
                CallbackQueryHandler(cancel_subscription, pattern="^" + str(CANCEL_SUBSCRIPTION) + "$"),
                CallbackQueryHandler(back_to_main_menu, pattern="^" + str(MAIN_MENU) + "$")

            ],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    application.add_handler(conv_handler)
    loop = asyncio.get_event_loop()

    loop.create_task(start_schedules(forwarder))
    application.run_polling()
    app.stop()


async def start_schedules(forwarder: MessageForwarder):
    schedule.every(1).hours.do(sync_data, forwarder=forwarder)

    while True:
        await asyncio.sleep(60)
        await schedule.run_pending()


if __name__ == "__main__":
    main()
