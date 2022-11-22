import json

from telegram import InlineKeyboardButton

from bot.navigation.constants import (
    APARTMENTS_STATE,
    HOUSES_STATE,
    SUBSCRIPTION_STATE,
    TOTAL_USERS_STATE,
    RECENT_HOUR_USERS_STATE,
    TOTAL_SUBSCRIBED_USERS_STATE,
    REFRESH_DB_STATE,
    ADMIN_MENU_STATE,
    CANCEL_SUBSCRIPTION_STATE,
    MAIN_MENU_STATE, RENT_STATE, ADS_STATE, ADS_APS_STATE, SUBMIT_HELP_STATE, CHECK_GEOLINK_STATE, SUBMIT_STATE)

# Buttons patterns
START_BUTTONS = {
    "Шукаю оренду": RENT_STATE,
    "Хочу здати в оренду": ADS_STATE,
}
RENT_BUTTONS = {
    "Оренда Квартир 🏢": APARTMENTS_STATE,
    "Оренда Будинків 🏡": HOUSES_STATE,
    "Повідомлення про нові оголошення 📩": SUBSCRIPTION_STATE,
}
ADS_BUTTONS = {
    "Здати квартиру 🏢": ADS_APS_STATE,
    # "Здати будтинок 🏢": ADS_HOUSES_STATE,
}

SUBSCRIPTION_BUTTONS = {
    "Квартири 🏢": APARTMENTS_STATE,
    "Будинки 🏡": HOUSES_STATE,
}

ADMIN_BUTTONS = {
    "Всього користувачів": TOTAL_USERS_STATE,
    "За минулу годину": RECENT_HOUR_USERS_STATE,
    "Всього з підпискою": TOTAL_SUBSCRIBED_USERS_STATE,
    "Оновити базу": REFRESH_DB_STATE,
    "Перевірити геолінки": CHECK_GEOLINK_STATE,
}
# Buttons Texts
HOME_MENU_BTN_TEXT = "🏠️"
LOAD_MORE_LINKS_BTN_TEXT = "Показати ще ⤵️"
BACK_BTN_TEXT = "⬅️"
SUBSCRIPTION_BTN_TEXT = "Підписатися на оновлення 📩"
ADMIN_MENU_BTN_TEXT = "Меню Адміна"
CANCEL_SUBSCRIPTION_BTN_TEXT = "Відмінити підписку ❌"
NEXT_BTN_TEXT = "Далі ➡️"
SKIP_BTN_TEXT = "Пропустити ➡"

# Buttons Callbacks
ACTION_NEXT = "n"
ACTION_BACK = "b"
ACTION_USER_SUBSCRIBE = "user_sub"
ACTION_SELF_SUBSCRIBE = "self_sub"
MAIN_MENU = "m"
ACTION_SUBSCRIBE = "sub"
SHOW_NEXT_PAGE = "else"

# Static Buttons
NEXT_PAGE_BTN = [
    InlineKeyboardButton(
        LOAD_MORE_LINKS_BTN_TEXT, callback_data='{"%s": 1}' % SHOW_NEXT_PAGE
    )
]
HOME_MENU_BTN = InlineKeyboardButton(
    HOME_MENU_BTN_TEXT, callback_data='{"%s": 1}' % MAIN_MENU
)
MAIN_MENU_BTN = InlineKeyboardButton(BACK_BTN_TEXT, callback_data=MAIN_MENU_STATE)
SUBMIT_HELP_BTN = InlineKeyboardButton(text="Попросити про допомогу", callback_data=SUBMIT_HELP_STATE)
SUBMIT_BTN = InlineKeyboardButton(text="Підтвердити", callback_data=SUBMIT_STATE)

SUBSCRIPTION_BTN = InlineKeyboardButton(
    SUBSCRIPTION_BTN_TEXT, callback_data='{"%s":1}' % ACTION_SUBSCRIBE
)
ADMIN_MENU_BTN = InlineKeyboardButton(
    ADMIN_MENU_BTN_TEXT, callback_data=ADMIN_MENU_STATE
)
CANCEL_SUBSCRIPTION_BTN = InlineKeyboardButton(
    CANCEL_SUBSCRIPTION_BTN_TEXT, callback_data=CANCEL_SUBSCRIPTION_STATE
)
SUBSCRIBE_USER_BUTTONS = {
    "Підписати себе": json.dumps({ACTION_SELF_SUBSCRIBE: 1}),
    "Підписати користувача": json.dumps({ACTION_USER_SUBSCRIBE: 1}),
}


def get_next_btn(text: str, callback: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=callback)


def get_back_btn(
        text: str = BACK_BTN_TEXT, callback: str = '{"%s":1}' % ACTION_BACK
) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=callback)


def SELECT_ALL_BTN(text: str, callback: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=callback)


def get_regular_btn(text: str, callback: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=callback)
