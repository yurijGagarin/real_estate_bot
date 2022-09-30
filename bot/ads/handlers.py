from telegram import Update
from telegram.ext import ContextTypes

from bot.ads.context.manager import Manager
from bot.ads.context.questions import QUESTIONS_DEFINITION
from bot.ads.navigation.constants import ADS_DIALOG_STAGE, START_STAGE
from bot.navigation.basic_keyboard_builder import show_ads_menu
from bot.navigation.constants import ADS_STAGE


async def ads_dialog_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    m = Manager(
        questions_definition=QUESTIONS_DEFINITION,
        update=update,
        context=context,
    )

    continue_flow = await m.process_action()

    if continue_flow:
        return ADS_DIALOG_STAGE

    await show_ads_menu(update, context)
    return ADS_STAGE
