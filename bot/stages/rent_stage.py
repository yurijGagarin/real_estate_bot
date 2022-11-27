from typing import Type, List

from telegram import Update
from telegram.ext import ContextTypes

from bot.context.filters import BaseFilter
from bot.context.manager import Manager
from bot.context.message_forwarder import MessageForwarder
from bot.context.state import State
from bot.db import get_user, save_user
from bot.models import Ad
from bot.navigation.basic_keyboard_builder import show_menu
from bot.navigation.buttons_constants import RENT_BUTTONS, SUBSCRIPTION_BUTTONS
from bot.navigation.constants import RENT_MENU_TEXT, SUBSCRIPTION_TEXT, SUBSCRIPTION_STAGE, RENT_STAGE


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
