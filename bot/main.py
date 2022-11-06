import asyncio
import datetime
import re
from typing import Type, List

import aioschedule as schedule
import sentry_sdk
from pyrogram import Client
from telegram import Update, InputMediaPhoto
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
from bot.ads.handlers import ads_dialog_handler
from bot.ads.navigation.constants import ADS_DIALOG_STAGE
from bot.context.filters import (
    RoomsFilter,
    DistrictFilter,
    ResidentialComplexFilter,
    PriceFilter,
    AdditionalFilter, BaseFilter,
)
from bot.context.manager import Manager
from bot.context.message_forwarder import MessageForwarder
from bot.context.state import State
from bot.data_manager import DataManager
from bot.db import (
    save_user,
    get_users_with_subscription,
    get_all_users,
    get_recent_users, get_user,
)
from bot.log import logging
from bot.models import Apartments, Houses, Ad
from bot.navigation.basic_keyboard_builder import (
    show_menu,
)
from bot.navigation.buttons_constants import SUBSCRIPTION_BUTTONS, START_BUTTONS, ADMIN_BUTTONS, RENT_BUTTONS, \
    ADS_BUTTONS
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
    MAIN_MENU_STATE, RENT_STAGE, RENT_STATE, ADS_STATE, ADS_STAGE, ADS_APS_STATE, SUBSCRIPTION_TEXT, MAIN_MENU_TEXT,
    RENT_MENU_TEXT, ADS_MENU_TEXT, )
from bot.notifications import notify_admins

logger = logging.getLogger(__name__)
sentry_sdk.init(dsn=config.SENTRY_DSN,
                traces_sample_rate=1.0,
                environment=config.SENTRY_ENV
                )


async def sync_data(forwarder: MessageForwarder):
    data_manager = DataManager()
    await data_manager.sync_data()
    await data_manager.notify_users(forwarder)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    user_logging = update.message.from_user
    logger.info("User %s started the conversation.", user_logging.first_name)
    # todo: uncomment when video help is needed
    # user = await get_user(update.effective_user.id)
    # if not user:
    #     await context.bot.send_message(chat_id=update.effective_user.id,
    #                                    text='Вітаємо вас в боті нерухомості.\n'
    #                                         'Якщо є якісь питання стосовно користування ботом,'
    #                                         ' можете подивитися відеоінструкцію.\n'
    #                                         'Відеоінструкція завжди доступна за командою /help ')
    #
    #     await forward_static_content(
    #         chat_id=update.effective_user.id,
    #         from_chat_id=config.STATIC_FROM_CHAT_ID,
    #         message_id=config.WELCOME_VIDEO,
    #         context=context
    #     )
    await show_menu(update=update,
                    context=context,
                    buttons_pattern=START_BUTTONS,
                    text=MAIN_MENU_TEXT,
                    items_in_a_row=1,
                    main_menu=True)

    return START_STAGE


async def rent_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    state = State.from_context(context)
    state.is_subscription = False
    state.update_context(context)
    await show_menu(update=update,
                    context=context,
                    buttons_pattern=RENT_BUTTONS,
                    text=RENT_MENU_TEXT,
                    )

    return RENT_STAGE


async def ads_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    await show_menu(update=update,
                    context=context,
                    buttons_pattern=ADS_BUTTONS,
                    text=ADS_MENU_TEXT,
                    )

    return ADS_STAGE


# todo: uncomment when videohelp is needed
# async def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
#     await forward_static_content(
#         chat_id=update.effective_user.id,
#         from_chat_id=config.STATIC_FROM_CHAT_ID,
#         message_id=config.WELCOME_VIDEO,
#         context=context
#     )
#     await show_menu(update=update,
#                     context=context,
#                     buttons_pattern=START_BUTTONS,
#                     text=MAIN_MENU_TEXT,
#                     items_in_a_row=1,
#                     main_menu=True)
#
#     return START_STAGE


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    notify_text = f"Користувач з Telegram ID: <b>{update.effective_user.id}</b>," \
                  f" Username: <b>@{update.effective_user.username}</b> потребує допомоги."
    await notify_admins(context.bot, notify_text)
    help_required_text = "Наш менеджер отримав Ваше прохання про допомогу" \
                         " та звʼяжется з вами найближчим часом.\n" \
                         "Ви можете продовжити користування ботом  Lviv City Estate"
    await show_menu(update=update,
                    context=context,
                    buttons_pattern=START_BUTTONS,
                    text=help_required_text,
                    items_in_a_row=1,
                    main_menu=True)

    return START_STAGE


async def subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    state = State.from_context(context)
    state.is_subscription = True
    state.update_context(context)
    await show_menu(update=update,
                    context=context,
                    buttons_pattern=SUBSCRIPTION_BUTTONS,
                    text=SUBSCRIPTION_TEXT,
                    subscription_menu=True)

    return SUBSCRIPTION_STAGE


async def cancel_subscription(
        update: Update, context: ContextTypes.DEFAULT_TYPE
) -> str:
    user = await get_user(update.effective_user.id)
    user.subscription = None
    user.subscription_text = None
    await save_user(user)
    await show_menu(update=update,
                    context=context,
                    buttons_pattern=SUBSCRIPTION_BUTTONS,
                    text=SUBSCRIPTION_TEXT,
                    subscription_menu=True)

    return SUBSCRIPTION_STAGE


async def back_to_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    await show_menu(update=update,
                    context=context,
                    buttons_pattern=START_BUTTONS,
                    text=MAIN_MENU_TEXT,
                    items_in_a_row=1,
                    main_menu=True)

    return START_STAGE


async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    await show_menu(update=update,
                    context=context,
                    buttons_pattern=ADMIN_BUTTONS,
                    admin_menu=True)

    return ADMIN_MENU_STAGE


async def get_total_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    users = await get_all_users()
    total_users = len(users)
    text = f"Всього користувачів: {total_users}"
    await show_menu(update=update,
                    context=context,
                    text=text,
                    buttons_pattern=ADMIN_BUTTONS,
                    admin_menu=True)
    return ADMIN_MENU_STAGE


async def get_recent_hour_users(
        update: Update, context: ContextTypes.DEFAULT_TYPE
) -> str:
    current_time = datetime.datetime.utcnow()
    last_hour = current_time - datetime.timedelta(hours=1)
    users = await get_recent_users(last_hour)
    total_users = len(users)
    text = f"Користувачів за останню годину: {total_users}"
    await show_menu(update=update,
                    context=context,
                    text=text,
                    buttons_pattern=ADMIN_BUTTONS,
                    admin_menu=True)
    return ADMIN_MENU_STAGE


async def get_total_users_with_subscription(
        update: Update, context: ContextTypes.DEFAULT_TYPE
) -> str:
    users = await get_users_with_subscription()
    total_users = len(users)
    text = f"Всього користувачів з підпискою: {total_users}"
    await show_menu(update=update,
                    context=context,
                    text=text,
                    buttons_pattern=ADMIN_BUTTONS,
                    admin_menu=True)
    return ADMIN_MENU_STAGE


def create_refresh_handler(forwarder: MessageForwarder):
    async def refresh_handler(
            update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> str:
        logger.info("success sync")
        await sync_data(forwarder=forwarder)
        text = "База даних оновлена.\nГарного вам дня 😊"
        await show_menu(update=update,
                        context=context,
                        text=text,
                        buttons_pattern=ADMIN_BUTTONS,
                        admin_menu=True)
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
        continue_flow, show_menu_args = await m.process_action()

        if continue_flow:
            return stage
        else:
            await m.reset_state()

        if show_menu_args is None:
            show_menu_args = {
                "update": update,
                "context": context,
                "buttons_pattern": RENT_BUTTONS,
                "text": RENT_MENU_TEXT,
            }
            if is_subscription:
                show_menu_args["buttons_pattern"] = SUBSCRIPTION_BUTTONS
                show_menu_args["text"] = SUBSCRIPTION_TEXT
                show_menu_args["subscription_menu"] = True
        await show_menu(**show_menu_args)

        if is_subscription:
            return SUBSCRIPTION_STAGE

        return RENT_STAGE

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
        },
        fallbacks=[CommandHandler("start", start),
                   CommandHandler("help", help)
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
