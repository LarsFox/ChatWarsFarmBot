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
        self.user = user
        self.phone = phone

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

    def get_message(self, entity, last=True, read=True):
        """
        Собирает последнее сообщение
        entity: адресат-entity
        last: повторяем сбор, пока последнее сообщение не от адресата
        read: отправляем сообщение о прочтении
        Возвращает сообщение и его содержимое для отображения
        """
        _, messages, senders = self.get_message_history(entity, 7)

        # Если есть отправители (не канал)
        if senders:
            # Отправляем уведомления, что мы прочитали сообщение
            if read:
                for i, sender in enumerate(senders):
                    if sender.id != self.user_id:
                        self.send_read_acknowledge(sender, messages[i])

            # Ждем, пока последним сообщением не будет ответ не от нас
            if last:
                for _ in range(15):
                    if senders[0].id != self.user_id:
                        break

                    _, messages, senders = self.get_message_history(entity, 7)
                    time.sleep(3)

            # Возвращаем пустой набор, если сообщений так и не было
            if not messages:
                return 0, None

        message = messages[0]

        if getattr(message, 'media', None):
            content = '<{}> {}'.format(
                message.media.__class__.__name__,
                getattr(message.media, 'caption', ''))

        elif hasattr(message, 'message'):
            content = message.message

        elif hasattr(message, 'action'):
            content = message.action

        else:
            content = message.__class__.__name__

        return message, content
