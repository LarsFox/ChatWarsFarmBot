# coding=utf-8
"""
Адаптированный клиент Телетона
"""

import sys
import time

from telethon import TelegramClient
from telethon.tl.functions.messages.forward_messages import (
    ForwardMessagesRequest)
from telethon.helpers import generate_random_long
from telethon.utils import get_input_peer
# from telethon.tl.functions.messages import ReadHistoryRequest
# from telethon.utils import get_input_peer

from sessions import API_ID, API_HASH


class TelethonClient(TelegramClient):
    """ Основной клиент для работы с Телеграмом """
    def __init__(self, user, phone):
        # Создаем файл сессии
        super().__init__("sessions/" + user, API_ID, API_HASH)
        self.user = user
        self.phone = phone
        self.user_id = 0

        self.user_id = 0

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
                code_ok = self.sign_in(self.phone, code)

            # Выходим, чтобы запросить код в следующей сессии
            sys.exit("Код верный! Перезапускай {}.".format(self.user))

        self.user_id = self.get_me().id

    '''
    def read_messages(self, entity, messages):
        """ Отправляет уведомление о прочтении сообщений """
        max_id = max(msg.id for msg in messages)
        return self.invoke(ReadHistoryRequest(peer=get_input_peer(entity), max_id=max_id))
    '''

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
