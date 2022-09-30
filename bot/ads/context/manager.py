import json
import os
from json import JSONDecodeError
from tempfile import TemporaryDirectory
from typing import List

from telegram import Update, InlineKeyboardMarkup, Message
from telegram.ext import ContextTypes

# from bot.ads.api.google import GoogleApi #TODO: fix it
from bot.ads.context.payload import Payload
from bot.ads.context.questions import BaseQuestion, QuestionDefinition, ADDRESS_Q_NAME, IMAGE_Q_NAME
from bot.ads.context.state import State
from bot.ads.navigation.buttons_constants import ACTION_NEXT, MAIN_MENU, ACTION_BACK, HOME_MENU_BTN
from bot.ads.navigation.constants import NAME_Q_NAME, CONTACT_Q_NAME, STATE_Q_NAME, ZHK_Q_NAME, ROOM_Q_NAME, \
    AREA_Q_NAME, \
    FLOOR_Q_NAME, PRICE_Q_NAME, ADDITIONAL_Q_NAME
from bot.ads.notifications import notify_admins


class Manager:
    questions: List[BaseQuestion]
    context: ContextTypes.DEFAULT_TYPE
    update: Update

    def __init__(
            self,
            questions_definition: List[QuestionDefinition],
            update: Update,
            context: ContextTypes.DEFAULT_TYPE,
    ):
        self.update = update
        self.context = context
        self.state = State.from_context(context)
        self.questions = []

        for i in range(len(questions_definition)):
            q = questions_definition[i]
            if i >= len(self.state.questions):
                self.state.questions.append(None)
            s = self.state.questions[i]
            question_obj = q.create_instance(state=s)
            self.questions.append(question_obj)

    async def process_action(self):
        payload = await self.get_payload()

        if ACTION_NEXT in payload.callback:
            if self.state.question_index < len(self.questions) - 1:
                self.move_forward()
            else:
                await self.show_result()
                return True
        elif ACTION_BACK in payload.callback:
            await self.questions[self.state.question_index].on_move_back(self.update, context=self.context)
            if self.state.question_index == 0:
                return False
            self.state.questions[self.state.question_index] = None
            self.move_back()
        elif MAIN_MENU in payload.callback:
            await self.reset_state()
            return False
        # else:
        result = await self.active_question.process_action(payload, self.update, context=self.context)
        self.state.questions[
            self.state.question_index
        ] = result

        await self.edit_message()
        self.save_state()
        return True

    async def get_payload(self):
        message = ""
        callback = {}
        file = None
        contact = None
        try:
            callback = json.loads(self.update.callback_query.data)
        except (JSONDecodeError, AttributeError):
            ...

        try:
            message = self.update.message.text
            file_id = None
            if self.update.message.photo:
                photo_size_list = self.update.message.photo
                file_id = photo_size_list[-1].file_id
            if self.update.message.document:
                document = self.update.message.document
                file_id = document.file_id
            if file_id is not None:
                file = await self.context.bot.get_file(file_id=file_id)

            if self.update.message.contact:
                contact = self.update.message.contact
        except (JSONDecodeError, AttributeError):
            ...

        return Payload(message=message, callback=callback, file=file, contact=contact)

    async def reset_state(self):
        self.state.questions = []
        self.state.question_index = 0
        self.save_state()

    def save_state(self):
        self.state.update_context(self.context)

    def move_forward(self):
        self.state.question_index += 1

    def move_back(self):
        self.state.question_index -= 1

    @property
    def active_question(self):
        return self.questions[self.state.question_index]

    async def edit_message(self, outer_text=None, outer_reply_markup=None, outer_navigation_row=True):
        navigation_row = []

        back_btn = self.active_question.build_back_btn()
        if back_btn is not None:
            if self.state.question_index >= 0:
                navigation_row.append(back_btn)

        next_btn = self.active_question.build_next_btn()
        if next_btn is not None:
            navigation_row.append(next_btn)

        kbrd = await self.active_question.build_keyboard()
        if outer_navigation_row:
            kbrd.append(navigation_row)

        text = ["Надані данні:\n"]
        for i in range(self.state.question_index + 1):
            f = self.questions[i]
            is_active = i == self.state.question_index
            text.append(await f.build_text(is_active=is_active))
        text = list(filter(None, text))
        keyboard = outer_reply_markup or InlineKeyboardMarkup(kbrd)
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

    async def show_result(self):
        await self._show_result()

    async def _show_result(self):
        api = GoogleApi()
        keyboard = []

        data_row = [
            str(self.update.effective_user.id),
        ]
        q_ids = {
            ADDRESS_Q_NAME: 0,
            IMAGE_Q_NAME: 0,
            NAME_Q_NAME: 0,
            CONTACT_Q_NAME: 0,
            STATE_Q_NAME: 0,
            ZHK_Q_NAME: 0,
            ROOM_Q_NAME: 0,
            AREA_Q_NAME: 0,
            FLOOR_Q_NAME: 0,
            PRICE_Q_NAME: 0,
            ADDITIONAL_Q_NAME: 0,
        }
        for i in range(self.state.question_index):
            q = self.questions[i]

            tmp_data = await q.build_data()
            if isinstance(tmp_data, list):
                data_row = data_row + tmp_data
            else:
                data_row.append(tmp_data)

            if q.question_name in q_ids:
                q_ids[q.question_name] = len(data_row) - 1

        files = data_row[q_ids[IMAGE_Q_NAME]]

        folder_name = str(self.update.effective_user.id)
        address = data_row[q_ids[ADDRESS_Q_NAME]]
        await self.edit_message(outer_text='Почекайте, відбувається збереження данних...',
                                outer_navigation_row=False)

        folder_id = await self.make_upload_to_gdrive(
            api=api,
            files=files,
            folder_name=folder_name,
            subfolder_name=address,
        )
        link_to_drive_folder = f'https://drive.google.com/drive/u/1/folders/{folder_id}'
        data_row[q_ids[IMAGE_Q_NAME]] = link_to_drive_folder
        new_data_row = [
            str(self.update.effective_user.id),
            data_row[q_ids[CONTACT_Q_NAME]],
            data_row[q_ids[NAME_Q_NAME]],
            data_row[q_ids[STATE_Q_NAME]],
            data_row[q_ids[ADDRESS_Q_NAME]],
            data_row[q_ids[ZHK_Q_NAME]],
            data_row[q_ids[ROOM_Q_NAME]],
            data_row[q_ids[AREA_Q_NAME]],
            data_row[q_ids[FLOOR_Q_NAME] - 1],
            data_row[q_ids[FLOOR_Q_NAME]],
            data_row[q_ids[PRICE_Q_NAME]],
            data_row[q_ids[ADDITIONAL_Q_NAME]],
            data_row[q_ids[IMAGE_Q_NAME] - 1],
            data_row[q_ids[IMAGE_Q_NAME]],
        ]
        # change фотографії на посилання
        data_to_spreadsheet = [new_data_row]

        api.update_values(data_to_spreadsheet)
        text_for_admins = f'Користувач з telegramID: {self.update.effective_user.id},\n' \
                          f'Який представився як {data_row[q_ids[NAME_Q_NAME]]},\n' \
                          f'З номером телефону: {data_row[q_ids[CONTACT_Q_NAME]]} \n' \
                          f'Створив новий обʼєкт. Перевірте будь ласка таблицю.'
        await notify_admins(text=text_for_admins, bot=self.context.bot)
        keyboard.append([HOME_MENU_BTN])
        text = 'Дані успішно збережені, наш менеджер звʼяжеться з вами найближчим часом'
        reply_markup = InlineKeyboardMarkup(keyboard)
        # todo: tmp_data workout
        await self.edit_message(outer_text=text, outer_reply_markup=reply_markup)
        self.save_state()

    async def make_upload_to_gdrive(self, api, files, folder_name, subfolder_name):
        file_paths = []
        with TemporaryDirectory() as tmpdir:
            for file in files:
                print(file)
                file_path = os.path.join(tmpdir, os.path.basename(file['file_path']))
                with open(file_path, 'wb') as f:
                    get_file = await self.context.bot.get_file(file_id=file['file_id'])
                    await get_file.download(out=f)
                file_paths.append(file_path)
            folder_id = await api.upload_files_to_gdrive(
                folder_name=folder_name,
                subfolder_name=subfolder_name,
                folder_from_upload=file_paths,
            )
        return folder_id
