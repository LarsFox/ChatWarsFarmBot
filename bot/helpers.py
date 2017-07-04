# coding=utf-8
"""
Вспомогательные функции и Логгер
"""

import datetime
import random
import re
import time

from bot.data import ATTACK, DEFEND, RIGHT, LEFT, EQUIP, \
                     WAR, GENITIVES, FIGHT


def get_equip(message):
    """ Возвращает словарь с лучшими предметами """
    equip = {ATTACK: {LEFT: 0, RIGHT: 0}, DEFEND: {LEFT: 0, RIGHT: 0}}

    for item in re.findall("(?<=_)[0-9]+", message):
        for weapon_type, hands in equip.items():
            for hand, weapon_id in hands.items():
                stats = EQUIP[hand].get(str(item), {}).get(weapon_type, 0)
                current = EQUIP[hand].get(weapon_id, 0)

                if stats > current:
                    equip[hand][weapon_type] = str(item)
                    break

    print(equip)
    return equip


def get_level(message):
    """ Извлекает уровень из профиля героя /hero """
    found = re.findall("Уровень: (.*?)\n", message)
    return int(found[0])


def get_flag(message):
    """ Извлекает флаг замка из профиля /hero """
    found = re.findall(".* замка", message)[0].split()
    return WAR[GENITIVES.get(found[-2])]


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
        """
        Выводит сообщение в консоль или в файл
        text: строка-сообщение для вывода
        """
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
        """
        Спит и выводит сообщение
        duration: целое число, длина сна в секундах
        message: строка, собственное сообщение в лог вместо «Сон в секундах»
        exact: добавление до 30 секунд к duration, по умолчанию False
        """
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
