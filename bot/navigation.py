from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update

# Stages
from bot.db import get_user

START_ROUTES = "START_STAGE"
APARTMENTS = "APARTMENTS_STAGE"
HOUSES = "HOUSES_STAGE"
END_ROUTES = "END_STAGE"
# Callback data
APARTMENTS_STATE = 'APARTMENTS_STATE'
HOUSES_STATE = 'HOUSES_STATE'
NEW_REAL_ESTATE_ALARM_STATE = 'NEW_REAL_ESTATE_ALARM_STATE'
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

# Main Menu Buttons

START_BUTTONS = {
    'Оренда Квартир': APARTMENTS_STATE,
    'Орена Будинків': HOUSES_STATE,
    # 'Повідомлення про нові оголошення': NEW_REAL_ESTATE_ALARM_STATE,
}


async def main_menu_buttons(user):

    keyboard = []
    row = []
    for k, v in START_BUTTONS.items():

        row.append(

            InlineKeyboardButton(k, callback_data=str(v)),

        )
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if len(row):
        keyboard.append(row)
    if user.is_admin:
        keyboard.append([InlineKeyboardButton("Оновити Базу",
                                              callback_data=REFRESH_DB)])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    return reply_markup


async def get_main_menu(update: Update):
    user = await get_user(update)
    reply_markup = await main_menu_buttons(user)
    if update.message:
        await update.message.reply_text(WELCOME_TEXT, reply_markup=reply_markup)
    elif update:
        await update.callback_query.edit_message_text(text=WELCOME_TEXT, reply_markup=reply_markup)
