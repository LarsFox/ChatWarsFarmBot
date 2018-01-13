# coding=utf-8
"""
Все локации для игры
"""
import random
import time


from bot.data import (
    SHORE, CAVE, CARAVANS, WOODS
)


ADVENTURES = [
    {"command": SHORE, "level": 0, "chance": 0},
    {"command": CAVE, "level": 0, "chance": 0},
    {"command": CARAVANS, "level": 0, "chance": 0},
    {"command": WOODS, "level": 0, "chance": 1},
]


class Location(object):
    """ Локация, любое место в игре, куда можем отправиться """

    def __init__(self, console, command, instant, prob):
        """
        console: название в консоли
        command: любое значение, на которое будет ориентироваться .emoji
        instant: требует ли выполнение команды времени
        after: время, через которое поход в локацию будет доступен
        """
        self.console = console
        self.command = command
        self.instant = instant
        self.prob = prob
        self.after = 0

    def postpone(self):
        """ Откладываем поход в локацию """
        seconds = random.random() * 1200 + 900
        self.after = time.time() + seconds
        return seconds / 60

    @property
    def travel(self):
        """ Определяет, идем или не идем в локацию """
        return random.random() <= self.prob

    @property
    def emoji(self):
        """ Возвращает команду, по которой осуществляется поход в локацию """
        return self.command

    def update(self, level, available):
        """ Метод обновления для перезаписи """
        pass


class Random(Location):
    """ Локация, в которой ходим по случайной команде """
    @property
    def emoji(self):
        """ Одна из случайных команд """
        return random.choice(self.command)


class Adventures(Location):
    """ Локация для всех приключений """

    def __init__(self, console, command, instant, prob):
        super().__init__(console, command, instant, prob)
        self.level = 0
        self.available = []

    @property
    def emoji(self):
        for command in self.command:
            if command["command"] not in self.available:
                continue

            if self.level < command["level"]:
                continue

            if random.random() > command["chance"]:
                continue

            return command["command"]

        return "/wtb_101"

    def update(self, level, available):
        """ Обновляет параметры, от которых зависит выбор локации """
        self.level = level
        self.available = [c["command"] for c in self.command
                          if c["command"].lower() in available.lower()]


RANDOM_COMMANDS = [
    "/hero",
    "/inv",
    "/report",
    "/trades",
    "/top",
    "/worldtop",
    "/wtb_113",
    "/wtb_115",
    "/wtb_116",
    "/wtb_117",
    "/wtb_121",
    "/wtb_179",
]


def create_locations():
    ''' Возвращает массив новых локаций '''
    # На индекс 2 жестко завязано обновление локаций из файла сессий
    return [
        Location("запрос героя", "🏅Герой", True, 0.7),
        Location("визит в замок", "🏰Замок", True, 0.6),
        Adventures("поход", ADVENTURES, False, 1),
        Random("случайную команду", RANDOM_COMMANDS, True, 0.7),
        # (!) 'arena': Location("поход на арену", "(!)", False),
        # (!) 'build': Location("поход на стройку", "/build_(!)", False),
    ]
