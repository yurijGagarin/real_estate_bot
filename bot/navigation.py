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
HOUSES_STATE = 'HOUSES_STATE'
SUBSCRIPTION_STATE = 'SUBSCRIPTION_STATE'
# Other constants
ACTION_NEXT = 'n'
ACTION_BACK = 'b'
MAIN_MENU = 'm'
REFRESH_DB = 'refresh_db'
SUBSCRIPTION_MODE = 'sub'
MAIN_MENU_TEXT = 'Головне Меню'
LOAD_MORE_LINKS_TEXT = "Показати"
LOAD_MORE_LINKS_BTN_TEXT = "Тут є ще вараінти для тебе"
MAIN_MENU_BTN_TEXT = "До головного меню"
WELCOME_TEXT = "Вітаємо вас в боті нерухомості. Оберіть бажану послугу."
CANCEL_SUBSCRIPTION = 'CANCEL_SUBSCRIPTION'
SUBSCRIPTION_TEXT = "Це меню для налаштування отримання нових повідомлень, " \
                    "коли зʼявляються обʼекти по вашим критеріям пошуку." \
                    " Для того щоб додати критерії до пошуку оберіть потрібний тип нерухомості."
SHOW_NEXT_PAGE = 'else'
SHOW_ITEMS_PER_PAGE = 3
NEXT_PAGE_BTN = [InlineKeyboardButton(LOAD_MORE_LINKS_TEXT,
                                      callback_data='{"%s": 1}' % SHOW_NEXT_PAGE)]
MAIN_MENU_BTN = InlineKeyboardButton(MAIN_MENU_BTN_TEXT,
                                     callback_data='{"%s": 1}' % MAIN_MENU)
MAIN_MENU_BTN_STATE = InlineKeyboardButton(MAIN_MENU_BTN_TEXT,
                                     callback_data=MAIN_MENU)
EMPTY_RESULT_TEXT = 'Нажаль за вашими критеріями пошуку нічого не знайшлось.' \
                    '\nСпробуйте змінити параметри пошуку,' \
                    '\nабо підпишіться на розсилку нових оголошень.'
BACK_BTN = InlineKeyboardButton('Назад', callback_data='{"b":1}')
SUBSCRIPTION_BTN = InlineKeyboardButton('Підписатися на оновлення', callback_data='{"sub":1}')
THATS_ALL_FOLKS_TEXT = 'Схоже що це всі оголошення на сьогодні,\n' \
                       'Підпишись на розсилку щоб першим знати про нові оголошення'
# Main Menu Buttons

START_BUTTONS = {
    'Оренда Квартир': APARTMENTS_STATE,
    'Оренда Будинків': HOUSES_STATE,
    'Повідомлення про нові оголошення': SUBSCRIPTION_STATE,
}
SUBSCRIPTION_BUTTONS = {
    'Квартири': APARTMENTS_STATE,
    'Будинки': HOUSES_STATE,
}


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_user(update)
    state = State()
    state.update_context(context)
    keyboard = await build_basic_keyboard(START_BUTTONS)
    if user.is_admin:
        keyboard.append([InlineKeyboardButton("Оновити Базу",
                                              callback_data=REFRESH_DB)])

    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text(WELCOME_TEXT, reply_markup=reply_markup)
    elif update:
        await update.callback_query.edit_message_text(text=WELCOME_TEXT, reply_markup=reply_markup)


async def show_subscription_menu(update: Update):
    user = await get_user(update)
    keyboard = await build_basic_keyboard(SUBSCRIPTION_BUTTONS)
    text = SUBSCRIPTION_TEXT
    if user.subscription:
        keyboard.insert(0, [InlineKeyboardButton("Відмінити підписку",
                                              callback_data=CANCEL_SUBSCRIPTION)])
        text = user.subscription_text
    keyboard.append([MAIN_MENU_BTN_STATE])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.callback_query.edit_message_text(text=text, reply_markup=reply_markup)


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
