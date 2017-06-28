# coding=utf-8
"""
Вспомогательные функции и Логгер
"""

import datetime
import random
import re
import time

from bot.data import FIGHT


def get_level(message):
    """ Извлекает уровень из профиля героя /hero """
    found = re.findall("Уровень: (.*?)\n", message)
    if found:
        return int(found[0])
    return 0


def get_fight_command(message):
    """ Извлекает команду боя в формате /fight_abcdef0123456789abc """
    if FIGHT in message:
        command = message.index(FIGHT)
        return message[command:command+27]

    return None


class Logger(object):
    """ Объект для записи сообщений, каждому — свой """
    def __init__(self, user, log_file):
        self.user = user
        self.log_file = log_file

    def log(self, text):
        """ Выводит в консоль или в файл """
        message = '[{0:%Y-%m-%d %H:%M:%S}/{1}] {2}'.format(
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
        """ Спит и выводит сообщение """
        if not exact:
            duration += random.random() * 30

        if message:
            if "{" in message:
                self.log(message.format(duration/60))

            else:
                self.log(message)

        else:
            self.log("Сон в секундах: {}".format(duration))

        time.sleep(duration)

        return True
