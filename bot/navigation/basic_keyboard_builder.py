from typing import Dict

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from bot.context.state import State
from bot.db import get_user_or_create_new, get_user
from bot.navigation.buttons_constants import (
    START_BUTTONS,
    ADMIN_MENU_BTN,
    SUBSCRIPTION_BUTTONS,
    CANCEL_SUBSCRIPTION_BTN,
    MAIN_MENU_BTN,
    ADMIN_BUTTONS,
)
from bot.navigation.constants import WELCOME_TEXT, SUBSCRIPTION_TEXT


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_user_or_create_new(update)
    state = State()
    state.update_context(context)
    keyboard = await build_basic_keyboard(START_BUTTONS)
    if user.is_admin:
        keyboard.append([ADMIN_MENU_BTN])

    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text(WELCOME_TEXT, reply_markup=reply_markup)
    elif update:
        await update.callback_query.edit_message_text(
            text=WELCOME_TEXT, reply_markup=reply_markup
        )


async def show_subscription_menu(update: Update):
    user = await get_user(update.effective_user.id)
    keyboard = await build_basic_keyboard(SUBSCRIPTION_BUTTONS)
    text = user.subscription_text or SUBSCRIPTION_TEXT
    if user.subscription:
        keyboard.insert(0, [CANCEL_SUBSCRIPTION_BTN])
        text = user.subscription_text
    keyboard.append([MAIN_MENU_BTN])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(
        text=text, reply_markup=reply_markup, parse_mode="HTML"
    )


async def show_admin_menu(
    update: Update, context: ContextTypes.DEFAULT_TYPE, text_outer: str = None
):
    user = await get_user(update.effective_user.id)
    keyboard = await build_basic_keyboard(ADMIN_BUTTONS, items_in_row=1)
    keyboard.append([MAIN_MENU_BTN])
    reply_markup = InlineKeyboardMarkup(keyboard)
    base_text = f"Вітаємо {user.nickname}, що адмінимо сьогодні?"
    text = base_text
    if text_outer is not None:
        text = text_outer

    await update.callback_query.edit_message_text(
        text=text, reply_markup=reply_markup, parse_mode="HTML"
    )


async def build_basic_keyboard(btns_pattern: Dict, items_in_row: int = 2):
    keyboard = []
    row = []
    for k, v in btns_pattern.items():
        row.append(
            InlineKeyboardButton(k, callback_data=str(v)),
        )
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if len(row):
        keyboard.append(row)
    return keyboard
