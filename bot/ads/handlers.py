from telegram import Update
from telegram.ext import ContextTypes

from bot.ads.context.manager import Manager
from bot.ads.context.questions import QUESTIONS_DEFINITION
from bot.ads.navigation.constants import ADS_DIALOG_STAGE
from bot.navigation.basic_keyboard_builder import show_menu
from bot.navigation.buttons_constants import ADS_BUTTONS
from bot.navigation.constants import ADS_STAGE, ADS_MENU_TEXT


async def ads_dialog_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    m = Manager(
        questions_definition=QUESTIONS_DEFINITION,
        update=update,
        context=context,
    )

    continue_flow = await m.process_action()

    if continue_flow:
        return ADS_DIALOG_STAGE
    await show_menu(update=update,
                    context=context,
                    buttons_pattern=ADS_BUTTONS,
                    text=ADS_MENU_TEXT,
                    )
    return ADS_STAGE
