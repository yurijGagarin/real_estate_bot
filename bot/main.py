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
    ConversationHandler,
    MessageHandler,
    filters,
)

from bot import config
from bot.context.filters import (
    RoomsFilter,
    DistrictFilter,
    ResidentialComplexFilter,
    PriceFilter,
    BaseFilter,
    AdditionalFilter,
)
from bot.context.manager import Manager
from bot.context.message_forwarder import MessageForwarder
from bot.context.state import State
from bot.data_manager import DataManager
from bot.db import (
    get_user,
    save_user,
    get_users_with_subscription,
    get_all_users,
    get_recent_users,
)
from bot.log import logging
from bot.models import Apartments, Houses, Ad
from bot.navigation.basic_keyboard_builder import (
    show_subscription_menu,
    show_main_menu,
    show_admin_menu,
)
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
    MAIN_MENU_STATE,
    SEND_MSGS_STATE,
)
from bot.notifications import send_message_to_users

logger = logging.getLogger(__name__)
sentry_sdk.init(dsn=config.SENTRY_DSN, traces_sample_rate=1.0)


async def sync_data(forwarder: MessageForwarder):
    data_manager = DataManager()
    await data_manager.sync_data()
    await data_manager.notify_users(forwarder)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    user_logging = update.message.from_user
    logger.info("User %s started the conversation.", user_logging.first_name)

    await show_main_menu(update, context)

    return START_STAGE


async def subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    state = State.from_context(context)
    state.is_subscription = True
    state.update_context(context)
    await show_subscription_menu(update)

    return SUBSCRIPTION_STAGE


async def cancel_subscription(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> str:
    user = await get_user(update)
    user.subscription = None
    user.subscription_text = None
    await save_user(user)
    await show_subscription_menu(update)

    return SUBSCRIPTION_STAGE


async def back_to_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    await show_main_menu(update, context)

    return START_STAGE


async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    await show_admin_menu(update, context)

    return ADMIN_MENU_STAGE


async def get_total_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    users = await get_all_users()
    total_users = len(users)
    text = f"Всього користувачів: {total_users}"
    await show_admin_menu(update, context, text)
    return ADMIN_MENU_STAGE


async def get_recent_hour_users(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> str:
    current_time = datetime.datetime.utcnow()
    last_hour = current_time - datetime.timedelta(hours=1)
    users = await get_recent_users(last_hour)
    total_users = len(users)
    text = f"Користувачів за останню годину: {total_users}"
    await show_admin_menu(update, context, text)
    return ADMIN_MENU_STAGE


async def get_total_users_with_subscription(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> str:
    users = await get_users_with_subscription()
    total_users = len(users)
    text = f"Всього користувачів з підпискою: {total_users}"
    await show_admin_menu(update, context, text)
    return ADMIN_MENU_STAGE


async def notify_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    users = await get_users_with_subscription()
    text = (
        "Доброго дня,\nВас турбує команда City Estate, ми хочемо сповістити Вас про те, що ми покращили функцію "
        "підписки на нові оголошення, просимо Вас відмінити Вашу підписку і створити нову. Гарного Вам дня. З "
        "повагою, команда City Estate. "
    )
    blocked_users = await send_message_to_users(bot=context.bot, users=users, text=text)
    users_to_delete = len(blocked_users)
    if users_to_delete:
        for user in blocked_users:
            user.subscription = None
            user.subscription_text = (
                f"З поверненням,{user.nickname}, ради Вас бачити знову."
            )
            await save_user(user)
    regular_text = f"Повідомлення надіслані"
    deleted_text = (
        regular_text
        + f"\nВсього було виявлено {users_to_delete} не активних користувачів"
    )

    text = deleted_text if users_to_delete else regular_text

    await show_admin_menu(update, context, text)
    return ADMIN_MENU_STAGE


# TODO Typing here
def create_refresh_handler(forwarder: MessageForwarder):
    async def refresh_handler(
        update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> str:
        logger.info("success sync")
        await sync_data(forwarder=forwarder)
        text = "База даних оновлена.\nГарного вам дня 😊"
        await show_admin_menu(update, context, text_outer=text)
        return ADMIN_MENU_STAGE

    return refresh_handler


def create_filter_handler(
    model: Type[Ad],
    filters: List[Type[BaseFilter]],
    stage: str,
    forwarder: MessageForwarder,
):
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
            return SUBSCRIPTION_STAGE

        await show_main_menu(update, context)
        return START_STAGE

    return handler


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
                    apartments_handler, pattern="^" + str(APARTMENTS_STATE) + "$"
                ),
                CallbackQueryHandler(
                    houses_handler, pattern="^" + str(HOUSES_STATE) + "$"
                ),
                CallbackQueryHandler(
                    admin_menu, pattern="^" + str(ADMIN_MENU_STATE) + "$"
                ),
                CallbackQueryHandler(
                    subscription, pattern="^" + str(SUBSCRIPTION_STATE) + "$"
                ),
            ],
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
                    notify_users, pattern="^" + str(SEND_MSGS_STATE) + "$"
                ),
                CallbackQueryHandler(
                    get_recent_hour_users,
                    pattern="^" + str(RECENT_HOUR_USERS_STATE) + "$",
                ),
                CallbackQueryHandler(
                    get_total_users_with_subscription,
                    pattern="^" + str(TOTAL_SUBSCRIBED_USERS_STATE) + "$",
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
                    back_to_main_menu, pattern="^" + str(MAIN_MENU_STATE) + "$"
                ),
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
