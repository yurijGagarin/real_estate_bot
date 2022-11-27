from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot.navigation.basic_keyboard_builder import show_menu
from bot.navigation.buttons_constants import HOME_MENU_BTN_TEXT, get_regular_btn, SUBMIT_HELP_BTN, MAIN_MENU_BTN, \
    START_BUTTONS
from bot.navigation.constants import MAIN_MENU_STATE, HELP_STAGE, START_STAGE
from bot.notifications import notify_admins


async def help_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    if update.message:
        context.user_data['user_help_message'] = update.message.text
        text = f'''Перевірте будь ласка ваше повідомлення.
Ваше повідомлення:
▶️<b>{context.user_data["user_help_message"]}</b> 

▪️ Якщо все гаразд, то натисніть кнопку <b><i>"Попросити про допомогу"</i></b>
▪️ Якщо бажаєте змінити повідомлення, то надішліть нове повідомлення.
▪️ Щоб повернутися в головне меню, то натисніть кнопку {HOME_MENU_BTN_TEXT}'''

        await update.message.delete()
        home_menu_btn = get_regular_btn(text=HOME_MENU_BTN_TEXT, callback=MAIN_MENU_STATE)
        reply_markup = InlineKeyboardMarkup([[SUBMIT_HELP_BTN], [home_menu_btn]])
        await context.bot.edit_message_text(text=text,
                                            chat_id=update.effective_user.id,
                                            message_id=context.user_data['help_menu_message_id'],
                                            reply_markup=reply_markup,
                                            parse_mode='HTML', )
    return HELP_STAGE


async def help_ask(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    text = 'Привіт! 😊 Це сервіс з оренди житла у Львові. Напиши, в чому саме потрібна допомога або консультація!'
    reply_markup = InlineKeyboardMarkup([[MAIN_MENU_BTN]])
    help_menu = await context.bot.send_message(chat_id=update.effective_user.id,
                                               text=text,
                                               parse_mode='HTML',
                                               reply_markup=reply_markup)
    context.user_data['help_menu_message_id'] = help_menu.id

    return HELP_STAGE


async def submit_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    notify_text = f"Користувач з Telegram ID: <b>{update.effective_user.id}</b>," \
                  f" Username: <b>@{update.effective_user.username}</b> потребує допомоги.\n" \
                  f"Повідомлення від користувача:\n{context.user_data['user_help_message']}"

    await notify_admins(context.bot, notify_text)
    help_required_text = "Наш менеджер отримав Ваше прохання про допомогу" \
                         " та звʼяжется з вами найближчим часом.\n" \
                         "Ви можете продовжити користування ботом Lviv City Estate"
    await show_menu(update=update,
                    context=context,
                    buttons_pattern=START_BUTTONS,
                    text=help_required_text,
                    items_in_a_row=1,
                    main_menu=True)
    return START_STAGE
