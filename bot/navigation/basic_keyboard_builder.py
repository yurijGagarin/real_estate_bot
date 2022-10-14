from typing import Dict

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from bot.context.state import State
from bot.db import get_user_or_create_new
from bot.navigation.buttons_constants import (
    ADMIN_MENU_BTN,
    CANCEL_SUBSCRIPTION_BTN,
    MAIN_MENU_BTN, )


async def show_menu(update: Update,
                    context: ContextTypes.DEFAULT_TYPE,
                    buttons_pattern: dict[str, ...],
                    items_in_a_row=2,
                    text: str = None,
                    main_menu: bool = False,
                    subscription_menu: bool = False,
                    admin_menu: bool = False):
    keyboard = await build_basic_keyboard(buttons_pattern, items_in_a_row)
    user = await get_user_or_create_new(update)
    if main_menu:
        state = State()
        state.update_context(context)
        if user.is_admin:
            keyboard.append([ADMIN_MENU_BTN])
    else:
        keyboard.append([MAIN_MENU_BTN])
    if subscription_menu:
        text = user.subscription_text or text
        if user.subscription:
            keyboard.insert(0, [CANCEL_SUBSCRIPTION_BTN])
            text = user.subscription_text
        # if user.is_admin:
        #     keyboard.insert(1, [get_regular_btn(text='Підписати користувача', callback=SUBSCRIBE_USER_STATE)])
    elif admin_menu:
        text = text or f"Вітаємо {user.nickname}, що адмінимо сьогодні?"
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="HTML")
    elif update:
        await update.callback_query.edit_message_text(
            text=text, reply_markup=reply_markup, parse_mode="HTML"
        )


async def build_basic_keyboard(btns_pattern: Dict, items_in_a_row):
    keyboard = []
    row = []
    for k, v in btns_pattern.items():
        row.append(
            InlineKeyboardButton(k, callback_data=str(v)),
        )
        if len(row) == items_in_a_row:
            keyboard.append(row)
            row = []
    if len(row):
        keyboard.append(row)
    return keyboard
