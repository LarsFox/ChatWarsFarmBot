# coding=utf-8
"""
Адаптированный клиент Телетона
"""

import os
import random
import sys
import time


from telethon import TelegramClient
from telethon.errors import RPCError
from telethon.helpers import generate_random_long
from telethon.tl.functions.messages.forward_messages import (
    ForwardMessagesRequest)
from telethon.tl.types import UpdateNewMessage
from telethon.utils import get_input_peer
# from telethon.tl.functions.messages import ReadHistoryRequest
# from telethon.utils import get_input_peer

from bot.data import (
    CHATS, TELEGRAM, GAME, TRADE, CAPTCHA, ENOT,
    PLUS_ONE, LEVEL_UP, ATTACK,
    SHORE,
    MONSTER_COOLDOWN
)
from bot.helpers import (
    count_help, get_fight_command, go_wasteland
)
from bot.locations import LOCATIONS
from bot.logger import Logger
from sessions import API_ID, API_HASH, SUPERGROUP


class FarmBot(TelegramClient):
    """ Объект бота для каждой сессии """

    # pylint: disable=too-many-instance-attributes
    # pylint: disable=too-many-return-statements

    def __init__(self, user, data, silent=True):
        # Если выводим в лог, очищаем его и начинаем с задержкой
        if silent:
            time.sleep(random.random() * 30)
            log_file = 'logs/' + user + '.log'
            with open(log_file, 'w') as target:
                target.truncate()

        else:
            log_file = None

        # Добавляем логгер
        self.logger = Logger(user, log_file, data['girl'])

        # Создаем файл сессии и устанавливаем параметры Телеграма
        # todo: here or later
        super().__init__("sessions/" + user, API_ID, API_HASH)

        # Массив с entity, которые будут использоваться для запросов через Телетон
        self.chats = {}

        # Телефон аккаунта
        self.phone = data['phone']

        # Название сессии для прямых команд боту
        self.user = user

        # self.user_id = 0

        # Состоятние бота
        # 0 — ничего не делаю
        # 1 — занят
        # 2 — жду ветер
        # 3 — выполняю прямую команду
        # -1 — заблокирован
        self.state = 0

        # Количество раз, которое осталось отправить прямую команду
        self.times = 0

        # Время до следующей передышки
        self.exhaust = time.time()
        
        # Все локации
        self.locations = LOCATIONS.copy()
        # Перезаписываем шансы локаций, если они указаны
        if "adventures" in data:
            self.locations[2].command = data["adventures"]

        # Время до следующего дня с походами к монстрам
        self.monster = time.time()

        # Последний приказ из Супергруппы
        self.order = None

        # Основной атрибут для увеличения каждый уровень
        self.primary = PLUS_ONE[ATTACK]
        # Перезаписываем характеристику, если она указана
        if LEVEL_UP in data:
            self.primary = PLUS_ONE[data[LEVEL_UP]]

        # Статус бота перед битвой
        self.status = None

        # Флаг, уровень и обмундирование определим позднее
        self.equipment = {}
        self.flag = None
        self.level = 0

        # Если запускаем в Виндоуз, переименовываем окно
        if os.name == 'nt':
            os.system("title " + user + " as FarmBot")

        # Поехали!
        self.logger.log("Сеанс {} открыт".format(user))

    def start(self):
        """ todo """
        self.connect_with_code()

        self.update_chats()
        self.add_update_handler(self.update_handler)
        # self.user_id = self.get_me().id

    def connect_with_code(self):
        """ Подключается к Телеграму и запрашивает код """
        # Подключаемся к Телеграму
        self.connect()

        # Если Телеграм просит код, вводим его и умираем
        # Каждый отдельный аккаунт запускаем через -l
        if not self.is_user_authorized():
            print('Первый запуск. Запрашиваю код...')
            self.send_code_request(self.phone)

            code_ok = False
            while not code_ok:
                code = input('Введите полученный в Телеграме код: ')

                # Двусторонняя верификация
                try:
                    code_ok = self.sign_in(self.phone, code)

                except RPCError as err:
                    if err.password_required:
                        verified = input(
                            'Введите пароль для двусторонней аутентификации: ')

                        code_ok = self.sign_in(password=verified)

                    else:
                        raise err

            # Выходим, чтобы запросить код в следующем боте
            sys.exit("Код верный! Перезапускай {}.".format(self.user))

    def update_handler(self, update):
        """ Получает обновления от Телетона и обрабатывает их """
        if self.state == -1:
            return

        if isinstance(update, UpdateNewMessage):
            message = update.message

            if message.from_id == TELEGRAM:
                self.telegram(message)

            elif message.from_id == GAME:
                self.game(message)

            elif message.from_id == SUPERGROUP:
                self.group(message)

            elif message.from_id == TRADE or message.from_id == ENOT:
                pass # todo: read

            elif message.from_id == CAPTCHA:
                pass # todo: resend


    def telegram(self, message):
        """ Записывает полученный от Телеграма код """
        if "Your login code" in message.message:
            self.logger.log(message.message[:23])

    def game(self, message):
        """ todo: комментарии к блокам и функции """
        text = message.message

        # Сообщения с ветром самые приоритетные
        if "завывает" in text:
            self.state = 2
            return

        # На приключении
        if "сейчас занят другим приключением" in text:
            self.state = 1
            return

        # Караваны
        if "/go" in text:
            self.state = 1
            self.send_message(self.chats[GAME], "/go")
            return

        # Прямые команды
        if self.state == 3:
            if "В казне" in text:
                self.state = 0
                self.send(self.chats[SUPERGROUP], "Не из чего строить!")
                return

            self.forward(self.chats[GAME], message.id, self.chats[SUPERGROUP])

            if self.times > 0:
                return

            self.state = 0
            self.send(self.chats[SUPERGROUP], "Все!")
            return

        if "Слишком много" in message.message:
            self.monster = time.time() + MONSTER_COOLDOWN
            return False

        if "/level_up" in message.message:
            self.logger.log("Ух-ты, новый уровень!")
            self.send(self.chats[GAME], "/level_up")
            return

        if "какую характеристику ты" in message.message:
            self.send(self.chats[GAME], self.primary)
            self.level += 1
            self.send(self.chats[SUPERGROUP], "Новый уровень: `{}`!".format(self.level))
            return

    def group(self, message):
        """ todo """
        parts = message.message.split(": ")

        # Прямая команда должна состоять из двух частей, разделенных двоеточием
        if len(parts) == 2:
            text, times = count_help(parts[0], parts[1],
                                     self.flag, self.level, self.user)

            if text == "/stop":
                self.state = -1
                return

            if text == "/go":
                self.state = 0
                return

            delay = 90
            if "/repair" or "/build" in text:
                delay = 310

            self.state = 3
            self.times = times

            for _ in range(times):
                # Команда подходит, отправляем
                self.send(self.chats[GAME], text)
                self.logger.sleep(delay, "Сон прямого контроля")
                self.times = self.times - 1

            return

        # Игнорируем все, кроме прямых приказов и боев
        text = message.message
        command = get_fight_command(text)
        if not command:
            return

        # Не помогаем на побережье, если не контролируем побережье
        if SHORE in text:
            if self.flag not in text:
                return

        # Не помогаем в Пустошах, если не из Пустошей
        if not go_wasteland(self.flag, text):
            return

        # Не помогаем, если боев на сегодня слишком много
        if time.time() < self.monster:
            return False

        self.logger.log("Иду на помощь: {}".format(command))
        self.send(self.chats[GAME], command)
        self.send(self.chats[SUPERGROUP], "+")
        return

    def send(self, entity, text):
        """ Сокращение, потому что бот всегда использует Маркдаун """
        self.send_message(entity, text, markdown=True)  # todo: обновить с новым Телетоном

    def forward(self, from_entity, message_id, to_entity):
        """ Forwards a single message from an entity to entity """
        self.invoke(
            ForwardMessagesRequest(
                get_input_peer(from_entity),
                [message_id],
                [generate_random_long()],
                get_input_peer(to_entity)
            )
        )

    def update_chats(self):
        """ Обновляет список чатов на основе 100 последних диалогов """
        _, entities = self.get_dialogs(100)

        for entity in entities:
            if entity.id in CHATS:
                self.chats[entity.id] = entity

            elif entity.id == SUPERGROUP:
                self.chats[SUPERGROUP] = entity

        return True

    def get_message(self, entity, repeat=True):
        """
        Собирает последнее сообщение
        entity: адресат-entity
        repeat: повторяем сбор, пока не получим сообщение от адресата
        Возвращает сообщение и его содержимое
        """
        msgs, sndrs = [], []

        # if read:
        #     for i, sender in enumerate(senders):
        #         if sender.id != self.user_id:
        #             self.send_read_acknowledge(sender, messages[i])

        for _ in range(5):
            if msgs:
                break

            try:
                _, msgs, sndrs = self.get_message_history(entity, 10)

                if repeat:
                    for _ in range(15):
                        if sndrs[0].id == entity.id:
                            break

                        _, msgs, sndrs = self.get_message_history(entity, 10)
                        time.sleep(3)

            except AttributeError:
                time.sleep(5)

        # self.read_messages(entity, msgs)
        message = msgs[0]

        if getattr(message, 'media', None):
            content = '<{}> {}'.format(
                message.media.__class__.__name__,
                getattr(message.media, 'caption', ''))

        elif hasattr(message, 'message'):
            content = message.message

        # (!) разобраться с содержанием сообщения
        elif hasattr(message, 'action'):
            content = ""  # message.action.encode('utf-8')

        else:
            content = message.__class__.__name__

        return message, content
