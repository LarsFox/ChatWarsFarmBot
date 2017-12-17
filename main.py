# coding=utf-8
"""
Главный модуль запуска ботов
"""


import random as r
# import resource
import sys
import threading
import time
import traceback

import telethon

from bot.client import FarmBot
from sessions import SESSIONS, SUPERGROUP


class Main(object):
    """ Запуск бота """
    def __init__(self):
        self.silent = "-s" in sys.argv
        self.login = "-l" in sys.argv
        self.code = "-c" in sys.argv

        self.users = [
            arg.capitalize() for arg in sys.argv[1:]
            if "-" not in arg
        ]

        if not self.users:
            sys.exit("Запуск без пользователей невозможен")

        if " " in self.users[0]:
            self.users = self.users[0].split()

        reboot = "-r" in sys.argv
        self.reboots = {user: reboot for user in self.users}
        self.pipes = {user: 0 for user in self.users}

    def launch(self):
        """
        Запускает файл с параметрами:

        -s: выбираем куда логгировать: в файл или в консоль
        -l: проверяем логин и вводим телефон (только для одного пользователя)
        -r: «перезапуск»: все действия откладываются, чтобы не спамить

        все остальные аргументы будут приняты как имена сессии
        """
        # -l
        if self.login:
            if len(self.users) > 1:
                sys.exit("Логин возможен только для одного пользователя")

            user = self.users[0]
            params = SESSIONS.get(user)
            bot = FarmBot(user, params, self.silent)
            bot.connect()
            sys.exit("Код уже был введен!")

        # Остальной набор
        # jobs = []
        for _, user in enumerate(self.users):
            params = SESSIONS.get(user)
            if not params:
                continue

            worker = threading.Thread(target=self.launch_user,
                                      args=(user, params))

            # jobs.append(worker)
            worker.start()

    def launch_user(self, user, params):
        """
        Запускает конкретного бота
        user: название бота для лог-файла и файла сессии
        params: словарь с параметрами из sessions.py
        """
        while True:
            bot = FarmBot(user, params, self.silent)

            # Ошибку при первичном подключении обрабатываем отдельно
            try:
                # Начинаем с короткого сна
                if self.reboots[user]:
                    time.sleep(r.random() * 60)

                bot.start()

            except (ValueError, OSError,
                    telethon.errors.RPCError,
                    telethon.errors.BadMessageError) as err:
                bot.logger.log("Не могу подключиться, немного посплю")
                time.sleep(120 + 60*r.random())
                continue

            try:
                if self.reboots[user]:
                    for location in bot.locations:
                        location.postpone()

                    time.sleep(r.random() * 180)

                # Поехали
                bot.start()

            except OSError as err:
                bot.logger.log("Ошибка: " + str(err))
                time.sleep(60 * r.random())

            except telethon.errors.RPCError as err:
                bot.logger.log("Ошибка РПЦ: " + str(err))
                time.sleep(60 * r.random())

            except telethon.errors.BadMessageError:
                bot.logger.log("Плохое сообщение, немного посплю")
                time.sleep(120 + 60*r.random())

            except Exception as err:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                exc = traceback.format_exception(exc_type,
                                                 exc_value, exc_traceback)

                text = ''.join(exc)
                bot.send(bot.chats[SUPERGROUP], text)
                bot.logger.log(text)

                raise err

            finally:
                self.reboots[user] = True


def memory():
    """ Ограничивает потребление памяти
    https://stackoverflow.com/questions/41105733 """
    pass
    # todo
    # resource.setrlimit(resource.RLIMIT_AS, (128 * 1024 * 1024, -1))


if __name__ == '__main__':
    memory()

    try:
        MAIN = Main()
        MAIN.launch()

    except MemoryError:
        sys.stderr.write('\n\nERROR: Memory Exception\n')
        sys.exit(1)
