from typing import Dict

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update

# Stages
from telegram.ext import ContextTypes

from bot.context.state import State
from bot.db import get_user

START_ROUTES = "START_STAGE"
APARTMENTS = "APARTMENTS_STAGE"
HOUSES = "HOUSES_STAGE"
SUBSCRIPTION = "SUBSCRIPTION_STAGE"

END_ROUTES = "END_STAGE"
# Callback data
APARTMENTS_STATE = 'APARTMENTS_STATE'
APARTMENTS_SUB = 'APARTMENTS_SUB'
HOUSES_STATE = 'HOUSES_STATE'
HOUSES_SUB = 'HOUSES_SUB'
SUBSCRIPTION_STATE = 'SUBSCRIPTION_STATE'
# Other constants
ACTION_NEXT = 'n'
ACTION_BACK = 'b'
MAIN_MENU = 'm'
REFRESH_DB = 'refresh_db'
MAIN_MENU_TEXT = 'Головне Меню'
LOAD_MORE_LINKS_TEXT = "Показати"
LOAD_MORE_LINKS_BTN_TEXT = "Тут є ще вараінти для тебе"
MAIN_MENU_BTN_TEXT = "До головного меню"
WELCOME_TEXT = "Вітаємо вас в боті нерухомості. Оберіть бажану послугу."
CANCEL_SUBSCRIPTION = 'cancel_subscription'
SUBSCRIPTION_TEXT = "Це меню для налаштування отримання нових повідомлень, " \
                    "коли зʼявляються обʼекти по вашим критеріям пошуку." \
                    " Для того щоб додати критерії до пошуку оберіть потрібний тип нерухомості."

# Main Menu Buttons

START_BUTTONS = {
    'Оренда Квартир': APARTMENTS_STATE,
    'Орена Будинків': HOUSES_STATE,
    'Повідомлення про нові оголошення': SUBSCRIPTION_STATE,
}
SUBSCRIPTION_BUTTONS = {
    'Квартири': APARTMENTS_STATE,
    'Будинки': HOUSES_STATE,
}


async def main_menu_buttons(user):
    keyboard = await build_basic_keyboard(START_BUTTONS)
    if user.is_admin:
        keyboard.append([InlineKeyboardButton("Оновити Базу",
                                              callback_data=REFRESH_DB)])

    reply_markup = InlineKeyboardMarkup(keyboard)
    return reply_markup


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_user(update)
    state = State()
    state.update_context(context)
    reply_markup = await main_menu_buttons(user)
    if update.message:
        await update.message.reply_text(WELCOME_TEXT, reply_markup=reply_markup)
    elif update:
        await update.callback_query.edit_message_text(text=WELCOME_TEXT, reply_markup=reply_markup)


async def show_subscription_menu(update: Update):
    user = await get_user(update)
    reply_markup = await subscription_buttons(user)

    await update.callback_query.edit_message_text(text=SUBSCRIPTION_TEXT, reply_markup=reply_markup)


async def subscription_buttons(user):
    keyboard = await build_basic_keyboard(SUBSCRIPTION_BUTTONS)
    # if user.subscription:
    #     keyboard.append([InlineKeyboardButton("Відмінити підписку",
    #                                           callback_data=CANCEL_SUBSCRIPTION)])
    # TODO: add handler user.subscription = None save_user(user)
    reply_markup = InlineKeyboardMarkup(keyboard)
    return reply_markup


async def build_basic_keyboard(btns_pattern: Dict):
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
