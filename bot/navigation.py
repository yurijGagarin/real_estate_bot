
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Stages
# TODO use string consts instread of numbers
START_ROUTES, APARTMENTS, HOUSES, END_ROUTES = range(4)
# Callback data
APARTMENTS_STATE = 'APARTMENTS_STATE'
HOUSES_STATE = 'HOUSES_STATE'

# TODO use string consts instread of numbers
THREE, FOUR = range(2)
ONE_ONE, ONE_TWO, ONE_THREE, ONE_FOUR = range(11, 15)

# Main Menu Buttons

START_BUTTONS = {
    'Оренда Квартир': APARTMENTS_STATE,
    'Орена Домів': HOUSES_STATE,
    'Повідомлення про нові оголошення': THREE,
}


async def main_menu_buttons():
    keyboard = [[]]
    for k, v in START_BUTTONS.items():
        keyboard[0].append(

            InlineKeyboardButton(k, callback_data=str(v)),

        )
    reply_markup = InlineKeyboardMarkup(keyboard)
    return reply_markup