# coding=utf-8
"""
Логгер
"""

import datetime
import random
import time

from bot.data import VERBS


LOG_STRING = '[{0:%Y-%m-%d %H:%M:%S} {1}] {2}'


class Logger(object):
    """ Объект для записи сообщений, каждому — свой """

    def __init__(self, user, log_file, girl):
        self.user = user
        self.log_file = log_file
        self.girl = girl

    def log(self, text):
        """
        Выводит сообщение в консоль или в файл
        text: строка-сообщение для вывода
        """
        message = LOG_STRING.format(
            datetime.datetime.now(),
            self.user,
            text
        )

        if self.log_file:
            with open(self.log_file, "a") as target:
                target.write(message + '\n')

        else:
            print(message)

    def sleep(self, duration, message=None, exact=True):
        """
        Спит и выводит сообщение
        duration: целое число, длина сна в секундах
        message: строка, собственное сообщение в лог вместо «Сон в секундах»
        exact: добавление до 30 секунд к duration, по умолчанию False
        """
        if not exact:
            duration += random.random() * 30

        if message:
            if "{}" in message:
                self.log(message.format(duration / 60))

            else:
                self.log(message)

        else:
            self.log("Сон в секундах: {}".format(duration))

        time.sleep(duration)

        return True

    def log_sexy(self, key, extra):
        """ Записывает определенный глагол в зависимости от пола """
        return self.log(VERBS[self.girl][key] + extra)
