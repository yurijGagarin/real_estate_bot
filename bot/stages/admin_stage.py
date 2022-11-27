import datetime
from typing import Optional
from urllib.parse import urlparse

from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot.api.google import GoogleApi
from bot.api.google_maps import GoogleMapsApi
from bot.context.message_forwarder import MessageForwarder, logger
from bot.data_manager import DataManager
from bot.db import get_recent_users, get_users_with_subscription, get_all_users, get_address_without_link, \
    write_data_to_geodata_table
from bot.navigation.basic_keyboard_builder import show_menu
from bot.navigation.buttons_constants import ADMIN_BUTTONS, get_regular_btn, HOME_MENU_BTN_TEXT, SUBMIT_BTN
from bot.navigation.constants import ADMIN_MENU_STAGE, MAIN_MENU_STATE, GEO_DATA_STAGE


async def get_recent_hour_users(
        update: Update, context: ContextTypes.DEFAULT_TYPE
) -> str:
    current_time = datetime.datetime.utcnow()
    last_hour = current_time - datetime.timedelta(hours=1)
    users = await get_recent_users(last_hour)
    total_users = len(users)
    text = f"Користувачів за останню годину: {total_users}"
    await show_menu(update=update,
                    context=context,
                    text=text,
                    buttons_pattern=ADMIN_BUTTONS,
                    admin_menu=True)
    return ADMIN_MENU_STAGE


async def get_total_users_with_subscription(
        update: Update, context: ContextTypes.DEFAULT_TYPE
) -> str:
    users = await get_users_with_subscription()
    total_users = len(users)
    text = f"Всього користувачів з підпискою: {total_users}"
    await show_menu(update=update,
                    context=context,
                    text=text,
                    buttons_pattern=ADMIN_BUTTONS,
                    admin_menu=True)
    return ADMIN_MENU_STAGE


async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    await show_menu(update=update,
                    context=context,
                    buttons_pattern=ADMIN_BUTTONS,
                    admin_menu=True)

    return ADMIN_MENU_STAGE


async def get_total_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    users = await get_all_users()
    total_users = len(users)
    text = f"Всього користувачів: {total_users}"
    await show_menu(update=update,
                    context=context,
                    text=text,
                    buttons_pattern=ADMIN_BUTTONS,
                    admin_menu=True)
    return ADMIN_MENU_STAGE


async def check_geolink(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    address_data = await get_address_without_link()
    if address_data is None:
        text = 'Всі адреси перевірені, повертайся пізніше.'
        await show_menu(update=update,
                        context=context,
                        text=text,
                        buttons_pattern=ADMIN_BUTTONS,
                        admin_menu=True)
        return ADMIN_MENU_STAGE

    context.user_data["address_pk"] = address_data.address
    context.user_data["district_pk"] = address_data.district

    google_query, text = address_data.build_google_query_and_user_text()

    api = GoogleMapsApi()
    geodata_result = api.get_geodata_by_address(google_query)

    home_menu_btn = get_regular_btn(text=HOME_MENU_BTN_TEXT, callback=MAIN_MENU_STATE)

    if geodata_result is None:
        text += f'\nБот не знайшов цю адресу на мапі за адресою:' \
                f'\n Вулиця: {context.user_data["address_pk"]}\nРайон: {context.user_data["district_pk"]}'

        reply_markup = InlineKeyboardMarkup([[home_menu_btn]])
    else:
        context.user_data["geodata_result"] = geodata_result

        text += f'\nБот знайшов таку позначку на мапі:\n\n{geodata_result["google_maps_link"]}\n\n'
        text += 'Якщо геомітка вас влаштовує, натисніть кнопку "Підтвердити", або надішліть своє посилання на гугл мапу.'

        reply_markup = InlineKeyboardMarkup([[SUBMIT_BTN], [home_menu_btn]])

    message = await update.callback_query.edit_message_text(text=text, reply_markup=reply_markup)
    context.user_data["message_id"] = message.message_id
    return GEO_DATA_STAGE


def parse_lat_lng_from_user_link(link: str) -> Optional[dict]:
    p = urlparse(link)
    split_geodata = p.path.split('@')
    if len(split_geodata) != 2:
        return None
    list_result = split_geodata[1].split(',')[0:2]

    return {'lat': list_result[0],
            'lng': list_result[1]}


async def user_geolink(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    coordinates = parse_lat_lng_from_user_link(update.message.text)
    home_menu_btn = get_regular_btn(text=HOME_MENU_BTN_TEXT, callback=MAIN_MENU_STATE)
    reply_markup = InlineKeyboardMarkup([[home_menu_btn]])

    text = f'Надайте правильне посилання, для обєкта за адресою:' \
           f'\n Вулиця: {context.user_data["address_pk"]}\nРайон: {context.user_data["district_pk"]}'
    if coordinates is not None:
        text = f'Ви встановили посилання для обєкта за адресою:' \
               f'\nВулиця: {context.user_data["address_pk"]}\nРайон: {context.user_data["district_pk"]}' \
               f'\n{update.message.text}'
        geodata_result = {
            'coordinates': coordinates,
            'google_maps_link': update.message.text,
        }
        context.user_data['geodata_result'] = geodata_result
        reply_markup = InlineKeyboardMarkup([[SUBMIT_BTN], [home_menu_btn]])

    await update.message.delete()
    await context.bot.edit_message_text(chat_id=update.effective_user.id,
                                        message_id=context.user_data["message_id"],
                                        text=text,
                                        reply_markup=reply_markup)

    return GEO_DATA_STAGE


async def submit_geolink(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    geodata_result = context.user_data['geodata_result']

    await write_data_to_geodata_table(address=context.user_data["address_pk"],
                                      district=context.user_data["district_pk"],
                                      map_link=geodata_result["google_maps_link"],
                                      coordinates=geodata_result["coordinates"],
                                      )
    name = 'Квартири'
    api = GoogleApi()
    spreadsheet_data = api.get_sheet_data(name)
    idxs = []
    for i, row in enumerate(spreadsheet_data):

        if context.user_data["address_pk"] in row and context.user_data["district_pk"] in row:
            idxs.append(i)
    link = geodata_result["google_maps_link"]
    api.batch_update_google_maps_link_by_row_idx(idxs, link)
    text = f"Посилання на гугл мапс для всіх обʼєктів з цією адресою встановлено."

    await show_menu(update=update,
                    context=context,
                    text=text,
                    buttons_pattern=ADMIN_BUTTONS,
                    admin_menu=True)
    return ADMIN_MENU_STAGE


async def sync_data(forwarder: MessageForwarder):
    data_manager = DataManager()
    await data_manager.sync_data()
    await data_manager.notify_users(forwarder)


def create_refresh_handler(forwarder: MessageForwarder):
    async def refresh_handler(
            update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> str:
        logger.info("success sync")
        await sync_data(forwarder=forwarder)
        text = "База даних оновлена.\nГарного вам дня 😊"
        await show_menu(update=update,
                        context=context,
                        text=text,
                        buttons_pattern=ADMIN_BUTTONS,
                        admin_menu=True)
        return ADMIN_MENU_STAGE

    return refresh_handler
