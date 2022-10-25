import json
import re
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Type

from telegram import Update, InlineKeyboardButton
from telegram.ext import ContextTypes

from bot.ads.context.payload import Payload
from bot.ads.navigation.buttons_constants import NEXT_BTN_TEXT, get_next_btn, get_back_btn, get_regular_btn
from bot.ads.navigation.constants import ANSWER, NEED_PHOTOGRAPHER_TEXT, HAVE_PHOTOS, IMAGE_Q_TEXT_ANSWER, \
    IMAGE_Q_PHOTOS_ANSWER, TEXT_ITEM_Q_TEXT_ANSWER, CONTACT_Q_NAME, NAME_Q_NAME, STATE_Q_NAME, ADDRESS_Q_NAME, \
    ZHK_Q_NAME, ROOM_Q_NAME, AREA_Q_NAME, FLOOR_Q_NAME, PRICE_Q_NAME, ADDITIONAL_Q_NAME, IMAGE_Q_NAME, \
    LAST_Q_NAME


class BaseQuestion:

    def __init__(self,
                 state: Optional[Dict],
                 question_name: str,
                 question_text: str,
                 ):
        self.desired_amount_of_rows = 2
        self.question_name = question_name
        self.question_text = question_text
        self.state = state or self.get_default_state()

    async def on_move_back(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        ...

    async def process_action(self, payload: Payload, update: Update, context: ContextTypes.DEFAULT_TYPE):
        return NotImplemented

    async def build_text(self, is_final=False, is_active=False):
        if self.has_answer():
            return f"✅ <b>{self.question_name}</b>: " + self.answer + "\n"
        return f"⏭ <b>{self.question_name}</b>: " + self.question_text + "\n"

    async def build_data(self) -> str:
        return self.answer

    async def build_keyboard(self) -> List[List[InlineKeyboardButton]]:
        """Helper function to build the next inline keyboard."""
        return []

    def build_next_btn(self):
        if self.has_answer():
            next_text = NEXT_BTN_TEXT
            return get_next_btn(next_text, '{"n":1}')
        return None

    def build_back_btn(self, use_default_back_btn_callback=False):
        return get_back_btn()

    def has_answer(self):
        return len(self.answer) > 0

    @property
    def answer(self) -> str:
        return self.state[ANSWER]

    @answer.setter
    def answer(self, v):
        self.state[ANSWER] = v

    def get_default_state(self) -> Dict:
        return {ANSWER: ''}


class TextQuestion(BaseQuestion):

    def __init__(self,
                 state: Optional[Dict],
                 question_name: str,
                 question_text: str,
                 sample: str = '',
                 answer_suffix='',
                 post_process_data=None,
                 validator=None,
                 integer_answer=False
                 ):
        self.sample = sample
        self.answer_suffix = answer_suffix
        self.post_process_data = post_process_data
        self.validator = validator
        self.integer_answer = integer_answer
        super().__init__(state, question_name, question_text)

    async def process_action(self, payload: Payload, update: Update, context: ContextTypes.DEFAULT_TYPE):
        answer = ''
        if payload.message:
            answer = (payload.message.strip())
            await update.message.delete()
        if answer:
            self.answer = answer
        return dict(self.state)

    async def build_text(self, is_final=False, is_active=False):
        text_without_answer_received = f"⏭ <b>{self.question_name}</b>: " + self.question_text + "\n" + self.sample
        alert_text = f"\n ❌ Введіть будь ласка коректні данні!"
        if self.has_answer():
            if self.validate_data():
                return f"✅ <b>{self.question_name}</b>: {self.answer} {self.answer_suffix}\n"
            else:
                return text_without_answer_received + alert_text
        return text_without_answer_received

    async def build_data(self) -> str:
        if callable(self.post_process_data):
            processed = self.post_process_data(self.answer)
            if len(processed) < 2:
                processed.append('--')
            return processed
        return await super().build_data()

    def validate_data(self):
        if callable(self.validator):
            return self.validator(self.answer)
        # if self.validate_pattern:
        #     reg_exp_validation = re.match(self.validate_pattern, self.answer)
        #     if reg_exp_validation:
        #         if self.question_name == ADDRESS_Q_NAME:
        #             contains_building_number = False
        #             if len(self.answer.split()) > 1:
        #                 contains_building_number = re.match(self.validate_pattern, self.answer.split()[-1])
        #             return reg_exp_validation and contains_building_number
        #         if self.integer_answer and self.question_name != FLOOR_Q_NAME:
        #             if int(self.answer) <= 0:
        #                 return None
        #         if self.question_name == FLOOR_Q_NAME:
        #             splited_answer = self.answer.split('/')
        #             slash_in_answer_false = len(splited_answer) != 2
        #             if slash_in_answer_false:
        #                 return None
        #             else:
        #                 floor_less_building_height = int(splited_answer[0]) <= int(splited_answer[1])
        #                 if not floor_less_building_height:
        #                     return None
        #     return reg_exp_validation
        return True

    def build_next_btn(self):
        if self.validate_data():
            return super().build_next_btn()
        return None


class ContactTextQuestion(TextQuestion):

    async def build_text(self, is_final=False, is_active=False):
        text_without_answer_received = f"⏭ <b>{self.question_name}</b>: " + self.question_text + "\n"
        alert_text = f"\n ❌ Введіть будь ласка коректний номер телефону!"
        if self.has_answer():
            if self.validate_data():
                return f"✅ <b>{self.question_name}</b>: {self.answer}\n"
            else:
                return text_without_answer_received + alert_text
        return text_without_answer_received

    # def validate_data(self):
    #     if self.validate_pattern:
    #         phone_number = ''.join(self.answer.split())
    #         reg_exp_validation = re.match(self.validate_pattern, phone_number)
    #         return reg_exp_validation
    #     return True


def validate_contact(answer):
    phone_number = ''.join(answer.split())
    reg_exp_validation = re.match(r"^(\+38)?(\d{10})$", phone_number)
    return reg_exp_validation


class ItemsQuestion(BaseQuestion):

    def __init__(self, state: Optional[Dict], question_name: str, question_text: str, items: List):
        self.items = items
        super().__init__(state, question_name, question_text)

    def get_default_state(self):
        return {
            ANSWER: {}
        }

    @property
    def selected_items(self) -> Dict:
        return self.state[ANSWER]

    @selected_items.setter
    def selected_items(self, v):
        self.state[ANSWER] = v

    def has_answer(self):
        items = self.get_items()
        return len(([k for k in items if self.selected_items.get(k)])) > 0

    async def process_action(self, payload: Payload, update: Update, context: ContextTypes.DEFAULT_TYPE):
        items = self.get_items()
        if ANSWER in payload.callback:
            key = items[payload.callback[ANSWER]]
            self.selected_items[key] = not self.selected_items.get(key)
        return dict(self.state)

    async def build_text(self, is_final=False, is_active=False):
        selected_values = len(list(filter(None, self.selected_items.values())))
        if selected_values:
            values = await self.get_text_answer()
            return f"✅ <b>{self.question_name}</b>: " + values + "\n"
        if is_active:
            return f"⏭ <b>{self.question_name}</b>: " + self.question_text + "\n"
        return f"✅ <b>{self.question_name}</b>: Не вказано \n"

    async def get_text_answer(self):
        items = self.get_items()
        values = ", ".join([k for k in items if self.selected_items.get(k)])
        return values

    def get_items(self):
        return self.items

    # todo: ccheck
    async def build_data(self) -> str:
        values = await self.get_text_answer()
        return values or 'Не надано'

    async def build_keyboard(self):
        items = self.get_items()
        keyboard = []
        row = []
        for i, item in enumerate(items):
            item_value = item
            data = json.dumps({
                ANSWER: i,
            })
            title = item_value
            if self.selected_items.get(item_value):
                title = f"{title} ✅"
            row.append(get_regular_btn(title, data))

            if len(row) == self.desired_amount_of_rows:
                keyboard.append(row)
                row = []
        if len(row):
            keyboard.append(row)

        return keyboard

    def build_next_btn(self):
        if self.question_name == 'Додаткова інформація':
            next_text = 'Пропустити ➡'
            if self.has_answer():
                next_text = NEXT_BTN_TEXT
            return get_next_btn(next_text, '{"n":1}')
        return super().build_next_btn()


class OneAnswerItemsQuestion(ItemsQuestion):

    def __init__(self, state: Optional[Dict], question_name: str, question_text: str, items: List):
        self.items = items
        super().__init__(state, question_name, question_text, items)

    async def process_action(self, payload: Payload, update: Update, context: ContextTypes.DEFAULT_TYPE):
        items = self.get_items()
        if self.selected_items:
            self.selected_items = {}
        if ANSWER in payload.callback:
            key = items[payload.callback[ANSWER]]
            self.selected_items[key] = not self.selected_items.get(key)
        return dict(self.state)


class TextItemsQuestion(ItemsQuestion):

    def __init__(self, state: Optional[Dict], question_name: str, question_text: str, items: List, sample: str,
                 validate_pattern=None):
        self.sample = sample
        self.validate_pattern = validate_pattern
        super().__init__(state, question_name, question_text, items)

    def get_default_state(self):
        state = super().get_default_state()
        state[TEXT_ITEM_Q_TEXT_ANSWER] = ''
        return state

    async def build_text(self, is_final=False, is_active=False):
        items = self.get_items()
        button_values = ", ".join([k for k in items if self.selected_items.get(k)])
        has_button_values = len(button_values) > 0
        text_without_answer_received = f"⏭ <b>{self.question_name}</b>: " + self.question_text + "\n" + self.sample
        alert_text = f"\n ❌ Введіть будь ласка коректні данні!"

        if has_button_values:
            return f"✅ <b>{self.question_name}</b>: " + button_values + "\n"
        if self.state.get(TEXT_ITEM_Q_TEXT_ANSWER):
            if self.validate_data():
                return f"✅ <b>{self.question_name}</b>: " + self.state[TEXT_ITEM_Q_TEXT_ANSWER] + "\n"
            else:
                return text_without_answer_received + alert_text
        return text_without_answer_received

    async def process_action(self, payload: Payload, update: Update, context: ContextTypes.DEFAULT_TYPE):
        answer = (payload.message.strip())
        if answer:
            self.state[ANSWER] = {}
            self.state[TEXT_ITEM_Q_TEXT_ANSWER] = None
            if self.validate_data():
                self.state[TEXT_ITEM_Q_TEXT_ANSWER] = answer
            await update.message.delete()
        else:
            self.state[TEXT_ITEM_Q_TEXT_ANSWER] = None
        await super().process_action(payload, update, context)
        return dict(self.state)

    def get_values_from_items(self):
        items = self.get_items()
        return ", ".join([k for k in items if self.selected_items.get(k)])

    async def get_text_answer(self):
        return self.get_values_from_items() or self.state.get(TEXT_ITEM_Q_TEXT_ANSWER, '')

    def get_items(self):
        return self.items

    def has_answer(self):
        return super().has_answer() or self.state.get(TEXT_ITEM_Q_TEXT_ANSWER)

    def validate_data(self):
        text_answer = self.state.get(TEXT_ITEM_Q_TEXT_ANSWER)
        if self.validate_pattern and text_answer:
            return re.match(self.validate_pattern, text_answer)
        return True

    def build_next_btn(self):
        if self.validate_data():
            return super().build_next_btn()
        return None


class ImageQuestion(BaseQuestion):
    OPTIONS = {
        NEED_PHOTOGRAPHER_TEXT: 'Потрібен фотограф',
        HAVE_PHOTOS: 'Маю фото',
    }

    def has_answer(self):
        img_t = self.state.get(IMAGE_Q_TEXT_ANSWER)
        photos = self.get_photos()
        return img_t == NEED_PHOTOGRAPHER_TEXT or (
                img_t == HAVE_PHOTOS and len(photos) > 0
        )

    def __init__(self, state: Optional[Dict], question_name: str, question_text: str, sample: str):
        self.sample = sample
        super().__init__(state, question_name, question_text)

    async def process_action(self, payload: Payload, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if 'img_back' in payload.callback:
            self.state[IMAGE_Q_TEXT_ANSWER] = None
        elif payload.message:
            await update.message.delete()
        elif payload.callback and IMAGE_Q_TEXT_ANSWER in payload.callback:
            self.state[IMAGE_Q_TEXT_ANSWER] = payload.callback[IMAGE_Q_TEXT_ANSWER]
        elif self.state.get(IMAGE_Q_TEXT_ANSWER) == HAVE_PHOTOS and payload.file:
            photos = self.get_photos()
            photos.append(payload.file.to_dict())
            self.state[IMAGE_Q_PHOTOS_ANSWER] = photos
            await update.message.delete()

        return dict(self.state)

    async def build_data(self):
        return [self.OPTIONS[self.state.get(IMAGE_Q_TEXT_ANSWER)], self.get_photos()]

    def get_photos(self):
        return self.state.get(IMAGE_Q_PHOTOS_ANSWER, [])

    async def build_text(self, is_final=False, is_active=False):
        if IMAGE_Q_TEXT_ANSWER in self.state:
            if self.state[IMAGE_Q_TEXT_ANSWER] == HAVE_PHOTOS:
                photos_cnt = len(self.get_photos())
                if photos_cnt > 0:
                    return f'✅ <b>{self.question_name}</b>: {photos_cnt}\n'
                return f'⏭ <b>{self.question_name}</b>: {self.sample}'
            if self.state[IMAGE_Q_TEXT_ANSWER] == NEED_PHOTOGRAPHER_TEXT:
                return f'✅ <b>{self.question_name}</b>: Потрібен фотограф\n'
        return f'⏭ <b>{self.question_name}</b>: {self.question_text}'

    async def build_keyboard(self) -> List[List[InlineKeyboardButton]]:
        """Helper function to build the next inline keyboard."""

        if self.state.get(IMAGE_Q_TEXT_ANSWER):
            return []
        return [[get_regular_btn(v, json.dumps({IMAGE_Q_TEXT_ANSWER: k}))] for k, v in self.OPTIONS.items()]

    def build_back_btn(self, use_default_back_btn_callback=False):
        if self.state.get(IMAGE_Q_TEXT_ANSWER):
            return get_back_btn(callback='{"img_back":1}')
        return super().build_back_btn()


# class ContactQuestion(BaseQuestion):
#
#     def __init__(self, state: Optional[Dict], question_name: str, question_text: str, sample: str):
#         self.sample = sample
#         super().__init__(state, question_name, question_text)
#
#     async def on_move_back(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
#         await context.bot.delete_message(
#             chat_id=update.effective_user.id,
#             message_id=self.state['contact_request_message_id'],
#         )
#         self.state['contact_request_message_id'] = None
#         r = await context.bot.send_message(chat_id=update.effective_user.id,
#                                            text='Зачекайте хвилинку...',
#                                            reply_markup=ReplyKeyboardRemove(remove_keyboard=True))
#         await context.bot.delete_message(
#             chat_id=update.effective_user.id,
#             message_id=r.message_id,
#         )
#
#     async def process_action(self, payload: Payload, update: Update, context: ContextTypes.DEFAULT_TYPE):
#         if payload.message:
#             await update.message.delete()
#         elif payload.contact:
#             if 'contact_request_message_id' in self.state:
#                 await context.bot.delete_message(
#                     chat_id=update.effective_user.id,
#                     message_id=self.state['contact_request_message_id'],
#                 )
#                 self.answer = '+' + update.message.contact.phone_number
#                 await update.message.delete()
#         else:
#             r = await context.bot.send_message(update.effective_user.id, self.sample,
#                                                reply_markup=ReplyKeyboardMarkup(keyboard=[[
#                                                    KeyboardButton('Надати контакт', request_contact=True)
#                                                ]], resize_keyboard=True), parse_mode="HTML")
#             self.state['contact_request_message_id'] = r.message_id
#
#         return dict(self.state)
#
#
class LastQuestion(BaseQuestion):
    def __init__(self, state: Optional[Dict], question_name: str, question_text: str):
        super().__init__(state, question_name, question_text)

    async def build_text(self, is_final=False, is_active=False):
        return f'{self.question_text}'

    def has_answer(self):
        return True

    async def process_action(self, payload: Payload, update: Update, context: ContextTypes.DEFAULT_TYPE):
        return dict(self.state)


@dataclass
class QuestionDefinition:
    class_name: Type[BaseQuestion]
    question_name: str
    question_text: str
    args: dict = field(default_factory=lambda: {})

    def create_instance(self, state: Optional[Dict]):
        args = {
            'state': state,
            'question_name': self.question_name,
            'question_text': self.question_text,
            **self.args
        }

        return self.class_name(**args)


QUESTIONS_DEFINITION = [
    # QuestionDefinition(
    #     class_name=ContactQuestion,
    #     question_name=CONTACT_Q_NAME,
    #     question_text='Не надано',
    #
    #     args={
    #         'sample': '❗Давайте для початку познайомимся.\n️Поділіться зі мною вашим контактом'
    #                   '\nнатиснувши кнопку <i>"Надати контакт"</i>'
    #
    #     }
    # ),

    QuestionDefinition(
        class_name=OneAnswerItemsQuestion,
        question_name=STATE_Q_NAME,
        question_text='Ви власник чи рієлтор?',

        args={
            'items': ['Власник', 'Рієлтор'],
        }
    ),

    QuestionDefinition(
        class_name=TextQuestion,
        question_name=ADDRESS_Q_NAME,
        question_text='Вкажіть адресу Вашої квартири.',
        args={
            'sample': '<b>\n ❗Відправляти повідомлення у форматі</b>:<i>\n "Назва вулиці" "Номер будинку"</i>'
                      '\nНаприклад:'
                      '\n--> <i>Трускавецька 2</i>'
                      '\n--> <i>Княгині Ольги 125а</i>',
            # 'validate_pattern': r'^[а-яА-Яє-їЄ-Ї \d]+$'
        }
    ),
    QuestionDefinition(
        class_name=TextItemsQuestion,
        question_name=ZHK_Q_NAME,
        question_text='Вкажіть Жк в якому знаходиться Ваша квартиру.',
        args={
            'sample': '\n❗<b>Наприклад:</b>'
                      '\n--> <i>Парус Парк</i>'
                      '\n--> <i>Львівський Дворик</i>'
                      '\nЯкщо Ви не знаєте назву ЖК, оберіть варіант <b>"Не знаю ЖК"</b> і натисніть <b>"Далі"</b>.',
            'items': ['Не знаю ЖК'],
            # 'validate_pattern': r'^[а-яА-Яє-їЄ-Ї \d]+$'

        }
    ),
    # add max
    QuestionDefinition(
        class_name=TextQuestion,
        question_name=ROOM_Q_NAME,
        question_text='Вкажіть кількість окремих кімнат.',

        args={
            'sample': '\n❗<b>Наприклад:</b>'
                      '\n--> <i>4</i>'
                      '\n--> <i>2</i>',
            # 'validate_pattern': r'^[0-9]+$',
            # 'integer_answer': True
        }
    ),
    QuestionDefinition(
        class_name=TextQuestion,
        question_name=AREA_Q_NAME,
        question_text='Вкажіть площу Вашої квартири.',

        args={
            'sample': '\n❗<b>Наприклад:</b>'
                      '\n--> <i>50</i>',
            'answer_suffix': 'м2',
            # 'validate_pattern': r'^[0-9.,]+$',
            # 'integer_answer': True
        }
    ),
    QuestionDefinition(

        class_name=TextQuestion,
        question_name=FLOOR_Q_NAME,
        question_text='Вкажіть поверх Вашої квартири, та поверхневість будинку.',

        args={
            'sample': '\n ❗️Поверх та поверхневість потрібно розділити знаком <b>"/"</b>'
                      '\n Наприклад:'
                      '\n --> <i>8/12</i>',
            'post_process_data': lambda a: a.split('/'),
            # 'validate_pattern': r'[0-9/]+$',
            # 'integer_answer': True
        }
    ),
    # QuestionDefinition(
    #     class_name=OneAnswerItemsQuestion,
    #     question_name=CURRENCY_Q_NAME,
    #     question_text='Оберіть валюту орендної плати.',
    #
    #     args={
    #         'items': ['USD',
    #                   'EUR',
    #                   'UAH',
    #                   ]
    #
    #     }
    # ),
    QuestionDefinition(
        class_name=TextQuestion,
        question_name=PRICE_Q_NAME,
        question_text='Напишіть ціну та валюту орендної плати.',

        args={
            'sample': '\n ❗Наприклад:'
                      '\n --> <i>15000 грн</i>'
                      '\n --> <i>1000 євро</i>'
                      '\n --> <i>600 usd</i>',
            # 'validate_pattern': r'^[0-9]+$',
            # 'integer_answer': True

        }
    ),
    QuestionDefinition(
        class_name=ItemsQuestion,
        question_name=ADDITIONAL_Q_NAME,
        question_text='Оберіть додаткову інформацію, яка допоможе швидше та якісніше здати квартиру'
                      '\n\n ❗️Оберіть всі потрібні варіанти та натисніть кнопку <b>"Далі"</b>,'
                      'або натисніть кнопку <b>"Пропустити"</b>',

        args={
            'items': ['Можна з тваринами',
                      'Можна з дітьми',
                      'Є кондиціонер',

                      ]

        }
    ),

    QuestionDefinition(
        class_name=ImageQuestion,
        question_name=IMAGE_Q_NAME,
        question_text='Якщо в вас є фотографії обʼєкта, натисніть кнопку <i>"Маю фото"</i>,\n'
                      'або натисніть кнопку <i>"Потрібен фотограф"</i>',
        # 'Ми не приймаємо обʼєкти нерухомості в яких немає фотографій',

        args={
            'sample': '\n ❗️Надішліть боту фотографії вашого обʼєкта.'
                      '\nМожливо відправити фотографії як файлом, так і звичайним фото.',
        }
    ),
    QuestionDefinition(
        class_name=TextQuestion,
        question_name=NAME_Q_NAME,
        question_text='Як до Вас звертатись?',
        args={
            'sample': '\n ❗Напишіть мені своє імʼя.',
            # 'validate_pattern': r'^[а-яА-Яє-їЄ-Ї]+$'
        }
    ),
QuestionDefinition(
        class_name=ContactTextQuestion,
        question_name=CONTACT_Q_NAME,
        question_text='Вкажіть Ваш контактний номер телефону.',
        args={
            # 'validate_pattern': r"^(\+38)?(\d{10})$",
            'validator': lambda x: validate_contact(x),
        }
    ),

    QuestionDefinition(
        class_name=LastQuestion,
        question_name=LAST_Q_NAME,
        question_text='\n❗️<b>Будь Ласка, перевірте ваші відповіді!'
                      '\nЯкщо щось не правильно,'
                      ' то ви можете повернутися назад та змінити їх</b>'
                      '\nЯкщо всі дані надано правильно, натисніть кнопку <b>Далі</b>,'
                      'та чекайте наступного повідомлення',
    )

]
