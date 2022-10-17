import datetime
import json
from json import JSONDecodeError
from typing import Type, List, Tuple, Optional

from sqlalchemy.ext.serializer import dumps
from sqlalchemy.sql import Select
from telegram import InlineKeyboardMarkup, Update, Message
from telegram.ext import ContextTypes

from bot.context.filters import BaseFilter
from bot.context.message_forwarder import MessageForwarder
from bot.context.payload import Payload
from bot.context.state import State
from bot.db import (
    get_result,
    save_user,
    delete_model_by_link,
    get_model_by_link, get_user,
)
from bot.exceptions import MessageNotFound
from bot.models import Ad
from bot.navigation.basic_keyboard_builder import show_menu
from bot.navigation.buttons_constants import (
    ACTION_BACK,
    MAIN_MENU,
    ACTION_SUBSCRIBE,
    SHOW_NEXT_PAGE,
    NEXT_PAGE_BTN,
    SUBSCRIPTION_BTN,
    ACTION_NEXT,
    get_back_btn,
    HOME_MENU_BTN, SUBSCRIBE_USER_BUTTONS, ACTION_SELF_SUBSCRIBE, ACTION_USER_SUBSCRIBE, SUBSCRIPTION_BUTTONS, )
from bot.navigation.constants import (
    SHOW_ITEMS_PER_PAGE,
    EMPTY_RESULT_TEXT,
    THATS_ALL_FOLKS_TEXT,
    LOAD_MORE_LINKS_TEXT, SUBSCRIBE_USER_TEXT, )
from bot.notifications import notify_admins


class Manager:
    filters: List[BaseFilter]
    query: Select
    context: ContextTypes.DEFAULT_TYPE
    update: Update
    model: Type[Ad]

    def __init__(
            self,
            model: Type[Ad],
            filters: List[Type[BaseFilter]],
            update: Update,
            context: ContextTypes.DEFAULT_TYPE,
            forwarder: MessageForwarder,
    ):
        self.update = update
        self.context = context
        self.state = State.from_context(context)
        self.filters = []
        self.forwarder = forwarder
        self.model = model

        prev_filter = None
        for i in range(len(filters)):
            f = filters[i]
            if i >= len(self.state.filters):
                self.state.filters.append(None)
            s = self.state.filters[i]
            filter_obj = f(state=s, prev_filter=prev_filter, model=model)
            prev_filter = filter_obj
            self.filters.append(filter_obj)

    def get_state(self):
        return self.state

    @property
    def active_filter(self):
        return self.filters[self.state.filter_index]

    @property
    def is_subscription(self):
        return self.state.is_subscription

    async def process_action(self) -> Tuple[bool, Optional[dict]]:
        payload = self.get_payload()

        if ACTION_NEXT in payload.callback:
            if self.state.filter_index < len(self.filters) - 1:
                self.move_forward()
            else:
                if self.is_subscription:
                    user_id_to_subscribe = self.update.effective_user.id
                    user = await get_user(user_id_to_subscribe)

                    if user.is_admin:
                        show_menu_args = {
                            "update": self.update,
                            "context": self.context,
                            "buttons_pattern": SUBSCRIBE_USER_BUTTONS,
                            "text": SUBSCRIBE_USER_TEXT,
                        }
                        await show_menu(**show_menu_args)
                        return True, None
                    await self.create_subscription(user_id=user_id_to_subscribe)
                    return False, None

                await self.show_result()
                return True, None
        elif ACTION_SELF_SUBSCRIBE in payload.callback:
            await self.create_subscription()
            return False, None
        elif ACTION_USER_SUBSCRIBE in payload.callback:
            edit_result = await self.update.callback_query.edit_message_text(
                text="Введіть Telegram ID користувача, якого ви бажаєте підписати.", parse_mode="HTML"
            )
            if isinstance(edit_result, Message):
                self.update.callback_query.message = edit_result
            self.context.user_data["callback_query"] = self.update.callback_query
            self.state.subscribe_user = True
            self.save_state()
            return True, None
        elif self.state.subscribe_user and payload.message:

            callback_query = self.update.callback_query
            if callback_query is None:
                callback_query = self.context.user_data["callback_query"]
            await self.update.message.delete()
            try:
                user = await get_user(int(payload.message))
                if user:
                    self.state.subscribe_user = False
                    self.save_state()
                    await self.create_subscription(user_id=user.id)
                    show_menu_args = {
                        "update": self.update,
                        "context": self.context,
                        "buttons_pattern": SUBSCRIPTION_BUTTONS,
                        "text": f"Ви підписали користувача з Telegram ID: <b>{user.id}</b>"
                                f" та з Username: <b>{user.nickname}</b> на оновлення.\n"
                                f"Гарного Дня",
                    }
                    return False, show_menu_args
            except ValueError:
                pass

            await callback_query.edit_message_text(
                text="Ми не знайшли користувача з таким Telegram ID. Спробуйте ще.", parse_mode="HTML"
            )
            return True, None

        elif ACTION_BACK in payload.callback:
            if self.state.filter_index == 0:
                return False, None
            self.state.filters[self.state.filter_index] = None
            self.move_back()
        elif SHOW_NEXT_PAGE in payload.callback:
            await self.show_result()
            return True, None
        elif MAIN_MENU in payload.callback:
            return False, None
        elif ACTION_SUBSCRIBE in payload.callback:
            await self.create_subscription()
            await self.show_result(just_subscribed=True)
            # await self.show_subscription_created()
            return True, None
            # return False, {
            #     "update": self.update,
            #     "context": self.context,
            #     "buttons_pattern": SUBSCRIPTION_BUTTONS,
            #     "text": SUBSCRIPTION_TEXT,
            #     "subscription_menu": True
            # }
        else:
            result = await self.active_filter.process_action(payload, self.update)
            self.state.filters[self.state.filter_index] = result

        await self.edit_message()
        self.save_state()
        return True, None

    async def reset_state(self):
        self.state.result_sliced_view = None
        self.state.filters = []
        self.state.filter_index = 0
        self.save_state()

    def move_forward(self):
        self.state.filter_index += 1

    def move_back(self):
        last_filter = len(self.state.filters) - 1
        if (
                self.state.filter_index == last_filter
                and self.state.result_sliced_view is not None
        ):
            self.state.result_sliced_view = None
            return
        self.state.filter_index -= 1

    async def edit_message(self, outer_text=None):
        kbrd = await self.active_filter.build_keyboard()
        navigation_row = []
        back_btn = self.active_filter.build_back_btn()
        next_btn = self.active_filter.build_next_btn()
        if back_btn is not None:
            if self.state.filter_index >= 0:
                navigation_row.append(back_btn)
        if next_btn is not None:
            navigation_row.append(next_btn)
        kbrd.append(navigation_row)
        text = ["Обрані фільтри:\n"]
        if self.state.is_subscription:
            text = [
                "Ви будете проінформовані про нові оголошення за такими критеріями:\n"
            ]
        for i in range(self.state.filter_index + 1):
            f = self.filters[i]
            is_active = i == self.state.filter_index
            text.append(await f.build_text(is_active=is_active))
        text = list(filter(None, text))
        keyboard = InlineKeyboardMarkup(kbrd)
        callback_query = self.update.callback_query
        if callback_query is None:
            callback_query = self.context.user_data["callback_query"]

        new_text = outer_text or "\n".join(text)

        # Edit message only if it has diff
        if (
                not self.context.user_data.get("callback_query")
                or new_text != callback_query.message.text
                or keyboard.inline_keyboard
                != callback_query.message.reply_markup.inline_keyboard
        ):
            edit_result = await callback_query.edit_message_text(
                text=new_text, reply_markup=keyboard, parse_mode="HTML"
            )

            if isinstance(edit_result, Message):
                callback_query.message = edit_result
            self.context.user_data["callback_query"] = callback_query

    def get_payload(self):
        message = ""
        callback = {}
        try:
            callback = json.loads(self.update.callback_query.data)
        except (JSONDecodeError, AttributeError):
            ...

        try:
            message = self.update.message.text
        except (JSONDecodeError, AttributeError):
            ...

        return Payload(message=message, callback=callback)

    async def show_result(self, just_subscribed=False):
        while True:
            try:
                await self._show_result(just_subscribed)
                break
            except MessageNotFound as e:
                print(e.message_link)
                await self.notify_admins_about_bad_link(e.message_link)
                await delete_model_by_link(self.model, e.message_link)

    async def _show_result(self, just_subscribed):
        await get_user(self.update.effective_user.id)
        q = await self.active_filter.build_query()
        all_items_result = await get_result(q, self.model)
        all_items_result_len = len(all_items_result)
        has_pagination = all_items_result_len > SHOW_ITEMS_PER_PAGE
        empty_result = not all_items_result_len
        keyboard = []
        page_offset = self.state.result_sliced_view or 0
        items_result = all_items_result[
                       page_offset: (page_offset + SHOW_ITEMS_PER_PAGE)
                       ]
        last_page = len(items_result) < SHOW_ITEMS_PER_PAGE
        user = await get_user(self.update.effective_user.id)

        subscription_text = await self.build_subscription_text()
        is_same_subscription = user.subscription_text == subscription_text

        text = ""
        if has_pagination and not last_page:
            page_offset += SHOW_ITEMS_PER_PAGE
            text = LOAD_MORE_LINKS_TEXT
            keyboard.append(NEXT_PAGE_BTN)

        keyboard.append([get_back_btn(), HOME_MENU_BTN])
        if not is_same_subscription:
            keyboard.append([SUBSCRIPTION_BTN])
        reply_markup = InlineKeyboardMarkup(keyboard)

        if empty_result:
            text = EMPTY_RESULT_TEXT
        if just_subscribed:
            text += f'\nВи підписалися на оновлення за цими критеріями ✅'
            return await self.update.callback_query.edit_message_text(
                text=text, reply_markup=reply_markup
            )
        if empty_result:
            return await self.update.callback_query.edit_message_text(
                text=text, reply_markup=reply_markup
            )
        if last_page:
            text = THATS_ALL_FOLKS_TEXT

        await self.forwarder.forward_estates_to_user(
            user_id=self.update.effective_user.id, message_links=items_result
        )
        await self.context.bot.send_message(
            chat_id=self.update.effective_chat.id, text=text, reply_markup=reply_markup
        )

        self.state.result_sliced_view = page_offset
        self.save_state()

    def save_state(self):
        self.state.update_context(self.context)

    async def build_subscription_text(self):
        text = ["Ви будете проінформовані про нові оголошення за такими критеріями:\n"]
        for i in range(self.state.filter_index + 1):
            f = self.filters[i]
            text.append(await f.build_text(is_final=True, is_active=False))
        return "\n".join(text)

    async def create_subscription(self, user_id=None):
        if user_id is None:
            user_id = self.update.effective_user.id
        user = await get_user(user_id)
        query = await self.active_filter.build_query()
        serialized = dumps(query)
        user.subscription = serialized
        user.subscription_text = await self.build_subscription_text()
        user.last_viewed_at = datetime.datetime.utcnow()
        await save_user(user)

    async def notify_admins_about_bad_link(self, message_link: str):
        model = await get_model_by_link(self.model, message_link)
        text = f"Something wrong with: {model.get_full_name()}"

        await notify_admins(self.context.bot, text)

    def show_subscription_created(self):
        pass
