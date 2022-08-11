from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Stages
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
MAIN_MENU_TEXT = 'Головне Меню'
LOAD_MORE_LINKS_TEXT = "Показати"
LOAD_MORE_LINKS_BTN_TEXT = "Тут є ще вараінти для тебе"
MAIN_MENU_BTN_TEXT = "До головного меню"
WELCOME_TEXT = "Вітаємо вас в боті нерухомості. Оберіть бажану послугу."

# Main Menu Buttons

START_BUTTONS = {
    'Оренда Квартир': APARTMENTS_STATE,
    'Орена Домів': HOUSES_STATE,
    # 'Повідомлення про нові оголошення': NEW_REAL_ESTATE_ALARM_STATE,
}


async def main_menu_buttons():
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

    reply_markup = InlineKeyboardMarkup(keyboard)
    return reply_markup
