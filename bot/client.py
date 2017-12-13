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
from telethon.tl.functions.messages.forward_messages import (
    ForwardMessagesRequest)
from telethon.helpers import generate_random_long
from telethon.utils import get_input_peer
# from telethon.tl.functions.messages import ReadHistoryRequest
# from telethon.utils import get_input_peer

from bot.data import (
    PLUS_ONE, LEVEL_UP, ATTACK
)
from bot.locations import LOCATIONS
from bot.logger import Logger
from sessions import API_ID, API_HASH #, SUPERGROUP


class FarmBot(TelegramClient):
    """ Объект бота для каждой сессии """

    # pylint: disable=too-many-instance-attributes

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
        self.user = user
        self.logger = Logger(user, log_file, data['girl'])

        # Создаем файл сессии и устанавливаем параметры Телеграма
        # todo: here or later
        super().__init__("sessions/" + user, API_ID, API_HASH)
        self.phone = data['phone']
        self.user_id = 0

        # Устанавливаем состояние
        # 0 — ничего не делаю
        # 1 — занят
        # 2 — жду ветер
        # 3 — выполняю прямую команду
        # 4 — заблокирован
        self.state = 0

        # Устанавливаем важные параметры
        self.exhaust = time.time()         # время до следующей передышки
        self.locations = LOCATIONS.copy()  # все локации
        self.monster = time.time()         # время до сражения с монстрами
        self.order = None                  # приказ из Супергруппы
        self.status = None                 # статус бота до и после битвы
        self.primary = PLUS_ONE[ATTACK]    # основной атрибут

        # Перезаписываем шансы локаций, если они указаны
        if "adventures" in data:
            self.locations[2].command = data["adventures"]

        # Запоминаем, какую характеристику увеличивать
        if LEVEL_UP in data:
            self.primary = PLUS_ONE[data[LEVEL_UP]]

        # Флаг, уровень и обмундирование определим позднее
        self.flag = None
        self.level = 0
        self.equipment = {}

        # Если запускаем в Виндоуз, переименовываем окно
        if os.name == 'nt':
            os.system("title " + user + " as FarmBot")

        # Поехали!
        self.logger.log("Сеанс {} открыт".format(user))

    def start(self):
        """ todo """
        self.connect_with_code()
        self.user_id = self.get_me().id

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

    def forward_message(self, from_entity, message_id, to_entity):
        """ Forwards a single message from an entity to entity """
        self.invoke(
            ForwardMessagesRequest(
                get_input_peer(from_entity),
                [message_id],
                [generate_random_long()],
                get_input_peer(to_entity)
            )
        )
