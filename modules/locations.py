# coding=utf-8
"""
Все локации для игры
"""
import random
import time


class Location(object):
    """
    Локация
    console: название в консоли
    command: любое значение, на которое будет ориентироваться .emoji
    instant: требует ли выполнение команды времени
    after: время, через которое поход в локацию будет доступен
    """
    def __init__(self, console, command, instant):
        self.console = console
        self.command = command
        self.instant = instant
        self.after = 0

    def postpone(self):
        """ Откладываем поход в локацию """
        seconds = random.random() * 1200 + 900
        self.after = time.time() + seconds
        return seconds / 60

    def travel(self, prob=0.7):
        """ Определяет, идем или не идем в локацию """
        if self.instant:
            if random.random() < prob:
                return True
            return False
        return True

    @property
    def emoji(self):
        """ Возвращает команду, по которой осуществляется поход в локацию """
        return self.command


class Random(Location):
    """ Локация, в которой ходим по случайной команде """
    @property
    def emoji(self):
        """ Одна из случайных команд """
        return random.choice(self.command)


RANDOM_COMMANDS = [
    "/top",
    "/worldtop",
    "/hero",
    # "/report",
    # "/inv",
    # "/trades"
]

LOCATIONS = [
    Location("запрос героя", "🏅Герой", True),
    Location("визит в замок", "🏰Замок", True),
    Location("поход в пещеру", "🕸Пещера", False),
    Location("поход в лес", "🌲Лес", False),
    Random("случайную команду", RANDOM_COMMANDS, True),
    # 'arena': Location("поход на арену", "(!)", False),
    # 'build': Location("поход на стройку", "/build_(!)", False),
]
