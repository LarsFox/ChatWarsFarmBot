# coding=utf-8
"""
Адаптированный клиент Телетона
"""

import sys
import time

import telethon

from sessions import API_ID, API_HASH


class TelethonClient(telethon.TelegramClient):
    """ Основной клиент для работы с Телеграмом """
    def __init__(self, user, phone):

        # Создаем файл сессии
        super().__init__("sessions/" + user, API_ID, API_HASH)

        # ... и подключаемся к Телеграму
        self.connect()

        # Если ТГ просит код, вводим его и умираем
        # Если много аккаунтов, запускаем через -l
        if not self.is_user_authorized():
            print('Первый запуск. Запрашиваю код...')
            self.send_code_request(phone)

            code_ok = False
            while not code_ok:
                code = input('Введите полученный в Телеграме код: ')
                code_ok = self.sign_in(phone, code)

            # Выходим, чтобы запросить код в следующей сессии
            sys.exit("{} код получил, перезапускай.".format(user))

    def get_message(self, entity, repeat=True):
        """
        Собираем последнее сообщение
        entity: адресат-entity
        repeat: повторяем сбор, пока не получим сообщение от адресата
        Возвращаем номер сообщения и его содержимое
        """
        _, messages, senders = self.get_message_history(entity, 1)

        if repeat:
            for _ in range(15):
                if senders[0].id == entity.id:
                    break

                _, messages, senders = self.get_message_history(entity, 1)
                time.sleep(3)

        message = messages[0]

        if getattr(message, 'media', None):
            content = '<{}> {}'.format(
                message.media.__class__.__name__,
                getattr(message.media, 'caption', ''))

        elif hasattr(message, 'message'):
            content = message.message

        elif hasattr(message, 'action'):
            content = message.action.encode('utf-8')

        else:
            content = message.__class__.__name__

        return message.id, content

    def send_text(self, entity, message):
        """ Отправляем сообщение определенному адресату-entity """
        self.send_message(entity, message, markdown=True, no_web_page=True)
