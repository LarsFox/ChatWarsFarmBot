# coding=utf-8
"""
Главный модуль запуска ботов
"""


import multiprocessing as mp
import random
import time
import sys


import telethon


from bot.bot import ChatWarsFarmBot
from sessions import SESSIONS


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
        -c: показываем код в запущенном ТГ (только для одного пользователя)
        -r: «перезапуск»: все действия откладываются, чтобы не спамить

        все остальные аргументы будут приняты как имена сессии
        """
        # -l
        if self.login:
            if len(self.users) > 1:
                sys.exit("Логин возможен только для одного пользователя")

            user = self.users[0]
            params = SESSIONS.get(user)
            bot = ChatWarsFarmBot(user, params, self.silent)
            sys.exit("Код уже был введен!")

        # -c
        if self.code:
            if len(self.users) > 1:
                sys.exit("Могу показать код только у одного пользователя")

            user = self.users[0]
            params = SESSIONS.get(user)
            bot = ChatWarsFarmBot(user, params, self.silent)
            _, message = bot.client.get_message(bot.chats["telegram"])
            sys.exit(message[:23])

        # Остальной набор
        queue = mp.JoinableQueue()

        for _, user in enumerate(self.users):
            params = SESSIONS.get(user)

            if not params:
                continue

            # Без флага не запускаем
            if "flag" not in params:
                continue

            worker = mp.Process(target=self.launch_user,
                                args=(user, params))

            worker.start()
            # worker.join()

        queue.join()

    def launch_user(self, user, params):
        """ Действие для каждого конкретного бота """
        # Очищаем лог, если перезапускаем вручную
        if self.silent:
            with open("logs/" + user + ".log", 'w') as target:
                target.truncate()

        while True:
            bot = ChatWarsFarmBot(user, params, self.silent)

            # Если выводим в консоль, начинаем без задержки
            if self.silent:
                bot.logger.sleep(random.random()*30, "Я люблю спать", False)

            # Перезагружаем и откладываем все действия
            if self.reboots[user]:
                for location in bot.locations:
                    location.postpone()

                bot.client.send_text(bot.chats["group"], "Перепросыпаюсь")

            else:
                # bot.updater.send_penguin()
                bot.client.send_text(bot.chats["group"], "Просыпаюсь")

            # Поехали
            try:
                bot.start()

            except OSError as err:
                bot.logger.log("Ошибка: " + str(err))
                time.sleep(60*random.random())

            except telethon.RPCError:
                bot.logger.log("Ошибка РПЦ, посплю немного")
                time.sleep(60*random.random())

            except telethon.BadMessageError:
                bot.logger.log("Плохое сообщение, немного посплю")
                time.sleep(120 + 60*random.random())

            self.reboots[user] = True


if __name__ == '__main__':
    MAIN = Main()
    MAIN.launch()
