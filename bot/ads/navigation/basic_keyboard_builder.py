from typing import Dict

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from bot.ads.context.state import State
from bot.ads.navigation.buttons_constants import START_BUTTONS
from bot.ads.navigation.constants import WELCOME_TEXT


async def build_basic_keyboard(btns_pattern: Dict, def_row=2):
    keyboard = []
    row = []
    for k, v in btns_pattern.items():
        row.append(
            InlineKeyboardButton(k, callback_data=str(v)),
        )
        if len(row) == def_row:
            keyboard.append(row)
            row = []
    if len(row):
        keyboard.append(row)
    return keyboard
