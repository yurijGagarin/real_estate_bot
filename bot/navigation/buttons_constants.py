from telegram import InlineKeyboardButton
# Buttons Patterns
from bot.navigation.constants import LOAD_MORE_LINKS_TEXT, MAIN_MENU_TEXT, APARTMENTS_STATE, HOUSES_STATE, \
    SUBSCRIPTION_STATE, TOTAL_USERS, RECENT_HOUR_USERS, TOTAL_SUBSCRIBED_USERS, REFRESH_DB, SHOW_NEXT_PAGE, MAIN_MENU, \
    MAIN_MENU_BTN_TEXT

START_BUTTONS = {
    'Оренда Квартир 🏢': APARTMENTS_STATE,
    'Оренда Будинків 🏡': HOUSES_STATE,
    'Повідомлення про нові оголошення 📩': SUBSCRIPTION_STATE,
}
SUBSCRIPTION_BUTTONS = {
    'Квартири 🏢': APARTMENTS_STATE,
    'Будинки 🏡': HOUSES_STATE,
}

ADMIN_BUTTONS = {
    'Всього користувачів': TOTAL_USERS,
    'За минулу годину': RECENT_HOUR_USERS,
    'Всього з підпискою': TOTAL_SUBSCRIBED_USERS,
    'Оновити базу': REFRESH_DB
}
# Buttons
NEXT_PAGE_BTN = [InlineKeyboardButton(LOAD_MORE_LINKS_TEXT,
                                      callback_data='{"%s": 1}' % SHOW_NEXT_PAGE)]
MAIN_MENU_BTN = InlineKeyboardButton(MAIN_MENU_TEXT,
                                     callback_data='{"%s": 1}' % MAIN_MENU)
MAIN_MENU_BTN_STATE = InlineKeyboardButton(MAIN_MENU_BTN_TEXT,
                                           callback_data=MAIN_MENU)
BACK_BTN = InlineKeyboardButton('⬅️', callback_data='{"b":1}')
SUBSCRIPTION_BTN = InlineKeyboardButton('Підписатися на оновлення 📩', callback_data='{"sub":1}')


def NEXT_BTN(text, callback):
    return InlineKeyboardButton(text=text, callback_data=callback)