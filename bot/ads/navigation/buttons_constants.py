from telegram import InlineKeyboardButton

# Handlers CallbackData States
RENT_STATE = "RENT_STATE"
HELP_STATE = "HELP_STATE"
MAIN_MENU_STATE = "MAIN_MENU_STATE"


# Buttons patterns
START_BUTTONS = {
    "Здати квартиру 🏢": RENT_STATE,
    # "Як користуватися ботом❔": HELP_STATE,
    "BACK": MAIN_MENU_STATE,
}
# Buttons Texts
HOME_MENU_BTN_TEXT = "🏠️"
BACK_BTN_TEXT = "⬅️"
NEXT_BTN_TEXT = "Далі ➡️"
SKIP_BTN_TEXT = "Пропустити ➡"

# Buttons Callbacks
ACTION_NEXT = "n"
ACTION_BACK = "b"
MAIN_MENU = "m"
SHOW_NEXT_PAGE = "else"

# Static Buttons
HOME_MENU_BTN = InlineKeyboardButton(
    HOME_MENU_BTN_TEXT, callback_data='{"%s": 1}' % MAIN_MENU
)
MAIN_MENU_BTN = InlineKeyboardButton(BACK_BTN_TEXT, callback_data=MAIN_MENU_STATE)


def get_next_btn(text: str, callback: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=callback)


def get_back_btn(
        text: str = BACK_BTN_TEXT, callback: str = '{"%s":1}' % ACTION_BACK
) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=callback)


def get_regular_btn(text: str, callback: str, ) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=callback)
