# coding=utf-8

import datetime
import multiprocessing as mp
import os
import random
import time
import sys

import telethon

from client import TelethonClient
from data import IMPORTANT, WAR, WAR_COMMANDS, COMMANDS, \
                 DEFEND, ATTACK, HERO, CASTLE, WOODS, CAVE, \
                 LOCATIONS, COOLDOWN, \
                 CARAVAN, FIGHT, LEVEL_UP, PLUS_ONE, EQUIP_ITEM

from sessions import API_ID, API_HASH, SUPERGROUP_ID, ENTER_CAVE, SESSIONS


class ChatWarsFarmBot():
    def __init__(self, user, params, silent=True):
        # Подключаемся к Телеграму
        self.client = TelethonClient(user, params['phone'])

        # Проверяем последние 10 диалогов
        _, entities = self.client.get_dialogs(10)

        # Создаем контакты по id из data
        for entity in entities:
            important = IMPORTANT.get(entity.id)

            if important:
                setattr(self, important, entity)

        # Собираем данные
        flag = params['flag']

        self.user = user
        self.silent = silent

        self.flag = WAR[flag]             # Флаг из sessions
        self.equipment = params["equip"]  # Снаряжение из sessions
        self.level = params["level"]      # Уровень из sessions
        self.girl = params["girl"]
        self.locations = LOCATIONS        # Локации из data

        self.exhaust = time.time()        # время отдышаться

        self.message = self.bot_message   # последнее сообщение от Бота
        self.old_id = 0                   # и его номер
        self.last_id = 0

        self.order = None                 # последний приказ в Супергруппе
        self.sent_defend = False          # отправляем 1 раз до и после боя

        # Выбираем формат вывода данных
        if self.silent:
            self.log_file = "logs/" + self.user + ".log"

        # Если запускаем в Виндоуз, переименовываем окно
        if os.name == 'nt':
            os.system("title " + self.user + " as ChatWarsFarmBot")

        # Поехали!
        self.log("Сеанс {} под флагом {} открыт".format(self.user, flag))

    def spam(self):
        while True:
            # Бой в 12:00. 11:00 в игре == 8:00 UTC+0
            now = datetime.datetime.utcnow()

            if not self.check_captcha():
                self.stop()

            # Защищаем КОРОВАНЫ
            self.caravan()

            # Сначала смотрим, кому можем помочь
            # Есть вероятность, что никто не поможет
            self.help_other()

            # (!) переписать для ранних приказов
            # С 47-й минуты ничего не делаем
            if (now.hour) % 4 == 0 and now.minute >= 47:
                # На 59-й идем в атаку
                if now.minute >= 59 and now.second >= 25:
                    self.attack()
                    self.sleep(45, "~Минутку посплю после приказа", False)

                # На 58-й уменьшаем время ожидания
                elif now.minute >= 58:
                    self.sleep(5, "Подбираюсь к отправке приказа")

                # С 54-й спим по минуте и заранее становимся в защиту
                elif now.minute >= 54:
                    self.defend()
                    self.sleep(60, "Сплю, пока битва близко")

                # С 47-й спим по две минуты
                else:
                    self.sleep(120, "Время перед битвой, сижу тихо")

            # До 7-й минуты ничего не делаем
            elif (now.hour-1) % 4 == 0 and now.minute < 7:
                self.sleep(180, "Жду, пока завывает ветер")
                self.wind()

            # В остальное время отправляем команды
            else:
                if time.time() > self.exhaust:
                    self.send_locations()
                    self.sleep(105, "~А теперь посплю пару минут", False)

                else:
                    self.sleep(105, "~Сил нет, сплю две минуты", False)

        return True

    # Системные функции

    @property
    def la(self):
        if self.girl:
            return "а"
        return ""

    def log(self, text, extra=""):
        """ Выводим в консоль или лог-файл """
        if self.silent:
            with open(self.log_file, "r") as target:
                history = target.read()

        message = '[{0:%Y-%m-%d %H:%M:%S}/{1}] {2}'.format(
            datetime.datetime.now(),
            self.user,
            text
        )

        if self.silent:
            with open(self.log_file, "w") as target:
                target.write("\n".join([history, message]) + extra)

        else:
            print(message)

    def sleep(self, duration, message=None, exact=True):
        """ Спим и логгируем """
        if not exact:
            duration += random.random() * 30

        if message:
            if "{" in message:
                self.log(message.format(duration/60))

            else:
                self.log(message)

        else:
            self.log("Ложусь спать на {:.3f} минут".format(duration/60))

        time.sleep(duration)

        return True

    def check_captcha(self):
        """ Проверяем капчу от бота """
        if "На выходе из замка" in self.message:
            self.log("Капча!")
            self.client.send_text(self.captcha_bot, self.message)
            self.sleep(10, "Десять секунд, на всякий случай жду Капчеватора")

            _, captcha_answer = self.client.get_message(self.captcha_bot)

            if "Не распознано" not in captcha_answer:
                self.log("Отдаю ответ")
                self.update_bot(captcha_answer)

                if "Ты отправился" in self.message:
                    self.log("Капча пробита!")
                    return True

                elif "Ты ответил правильно" in self.message:
                    self.log("Слишком просто!")
                    return True

            return False

        if "Не умничай" in self.message:
            return False

        elif "Не шути" in self.message:
            return False

        elif "вспотел" in self.message:
            return False

        return True

    def update_bot(self, message=None, sleep=5):
        """
        Отправляем сообщение Боту и ждем ответа
        message: сообщение к отправке
        sleep: пауза после отправки сообщения
        """
        if message:
            self.client.send_text(self.cw, message)
            self.sleep(sleep, "Сплю пять секунд после отправки сообщения")

        for i in range(1, 7):
            self.last_id, self.message = self.client.get_message(self.cw)

            if self.old_id == self.last_id:
                self.sleep(10, "Жду сообщение: {}/6".format(i))

            else:
                self.old_id = self.last_id
                break

        return self.check_captcha()

    def stop(self):
        """ Убиваем процесс """
        self.client.send_text(self.group, "У меня тут проблема")
        self.client.send_text(self.group, self.message)
        sys.exit()  # (!) проверить, выключаются ли все боты или один

    # Конец

    # Сокращения

    @property
    def bot_message(self):
        """ Последнее сообщение от бота игры """
        _, message = self.client.get_message(self.cw)
        return message

    @property
    def group_message(self):
        """ Последнее сообщение от Супергруппы """
        _, message = self.client.get_message(self.group, False)
        return message

    def send_penguin(self):
        """ Отправляем инвентарь Пингвину """
        if self.level < 15:
            return False

        self.client.send_text(self.trade_bot, "/start")
        self.sleep(3, "Отправляю инвентарь пингвину")

        _, message = self.client.get_message(self.trade_bot)
        self.client.send_text(self.penguin, message)
        return True

    # Конец

    # Бой

    def attack(self):
        """
        Считываем приказ из Супергруппы
        Считываем его
        Надеваем атакующую одежду
        """

        self.order = WAR.get(WAR_COMMANDS.get(self.group_message.lower()))

        if self.order and self.order != self.flag:
            self.hero(1)
            self.log("Иду в атаку")

            self.update_bot(ATTACK)

            self.log("Отправляю приказ из файла")
            self.update_bot(self.order)

            self.equip("attack")

        return True

    def defend(self):
        """ Отправляем приказ к защите """
        self.hero(1)

        if not self.sent_defend:
            if "Отдых" in self.message:
                self.log("Становлюсь в защиту")
                self.update_bot(DEFEND)

                if "будем держать оборону" in self.message:
                    self.update_bot(self.flag)

                self.sent_defend = True

        return True

    def wind(self):
        """
        Спим после боя
        Отправляем /report боту
        Надеваем защитную одежду
        Отписываемся о выполнении приказа в Супергруппу
        Забываем приказ
        """
        if self.sent_defend:
            self.report(1)

            if "завывает" not in self.message:
                if self.order is not None:
                    if self.order != self.flag:
                        self.client.send_text(
                            self.group,
                            "Атаковал" + self.la + " {}".format(self.order)
                        )
                        self.equip("defend")

                    else:
                        self.client.send_text(
                            self.group,
                            "Защищал" + self.la + " {}".format(self.order)
                        )

                    self.log("Приказ устарел, забываю его")
                    self.order = None

                else:
                    self.client.send_text(
                        self.group,
                        "Не увидел" + self.la + " приказ :("
                    )

                self.sent_defend = False
                self.send_penguin()

        return True

    def equip(self, state):
        for _, items in self.equipment.items():
            if len(items) == 2:
                item = EQUIP_ITEM.format(items[state])
                self.log("Надеваю: {}".format(item))
                self.update_bot(item, sleep=3)

        self.log("Завершаю команду {}".format(state))
        return True

    # Конец

    # Мирное время

    def postpone_location(self, location):
        delta = random.random() * 1200 + 900
        location.after = time.time() + delta

        self.log("Отправлю {} через {:.3f} минут".format(
            location.console,
            delta / 60
        ))

        return True

    def send_locations(self):
        for location in self.locations:
            wait = time.time() - location.after

            if wait > 0:
                self.log("Отправляю {}".format(location.console))
                gone = getattr(self, location.name)()

                if gone:
                    self.postpone_location(location)

        return True

    # Конец

    # Немедленные запросы (pay_visit)

    def hero(self, prob=0.7):
        """
        Запрашивает профиль героя
        И прокачивает уровень, если может
        """
        self.pay_visit(HERO, prob)

        if LEVEL_UP in self.message:
            self.log("Ух-ты, новый уровень!")
            self.update_bot(LEVEL_UP)

            if "какую характеристику ты" in self.message:
                self.update_bot(PLUS_ONE)

            else:
                self.log("Странно, где же выбор?")

        return True

    def worldtop(self):
        return self.pay_visit("/worldtop")

    def report(self, prob=0.7):
        return self.pay_visit("/report", prob)

    def commands(self):
        return self.pay_visit(random.choice(COMMANDS))

    def castle(self):
        return self.pay_visit(CASTLE)

    def pay_visit(self, command, prob=0.7):
        if random.random() < prob:
            self.update_bot(command)
            return self.check_captcha()

        return self.sleep(10, "Ничего не отправляю, просто сплю")


    # Конец

    # Пятиминутные действия (go)

    # def arena(self):
    #     # (!)
    #     return True

    # def build(self):
    #     # (!)
    #     return True

    def farm(self, prob=0.5):
        if self.level >= ENTER_CAVE:
            if random.random() < prob:
                return self.go(CAVE)
        return self.travel(WOODS)

    def travel(self, message):
        """
        Отправляет команду боту
        Откладывает все команды, если видит усталость
        Сражается, если видит монстра
        После запрашивает профиль героя, мол, изменилось ли что?
        """
        went = self.update_bot(message)

        if "мало единиц выносливости" in self.message:
            self.log("~Выдохся, поживу без приключений пару часов")
            self.exhaust = time.time() + COOLDOWN + random.random() * 3600
            return False

        if "сейчас занят другим приключением" in self.message:
            self.log("А, я же не дома")
            return False

        if went:
            self.sleep(310, "Вернусь через 5 минут")

        else:
            self.stop()

        self.fight()

        if random.random() < 0.4:
            self.hero()

        return True

    # Конец

    # Перехваты

    def extract_fight_command(self, message):
        if FIGHT in message:
            command = message.index(FIGHT)
            return message[command:command+27]

        return None

    def caravan(self):
        self.message = self.bot_message
        if CARAVAN in self.message:
            self.log("Защищаю караван")
            self.update_bot(CARAVAN)
            self.sleep(45, "~Минутку посплю после каравана", False)

        return True

    def help_other(self):
        command = self.extract_fight_command(self.group_message)

        if command:
            self.log("Иду на помощь: {}".format(command))
            self.client.send_text(self.group, "+")
            self.update_bot(command)

        return True

    def fight(self):
        self.message = self.bot_message
        command = self.extract_fight_command(self.message)

        if command:
            self.sleep(5, "А вот и монстр! Сплю пять секунд перед дракой")
            self.client.send_text(self.group, command)
            self.update_bot(command)

        return True

    # Конец


class Main(object):
    def __init__(self):
        """
        -s: логгируем в файл или в консоль
        -e: игнорирует все ошибки и спамит о них в Супергруппу
        -l: проверяем логин и вводим телефон (только для одного пользователя)
        -c: показываем код в запущенном ТГ (только для одного пользователя)
        -r: «перезапуск»: все действия откладываются, чтобы не спамить

        все остальные аргументы будут приняты как имена сессии
        """
        self.silent = "-s" in sys.argv
        self.avoid_errors = "-e" in sys.argv
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
            sys.exit(bot.client.get_message(bot.telegram)[1][:23])

        # Остальной набор
        queue = mp.JoinableQueue()

        for _, user in enumerate(self.users):
            params = SESSIONS.get(user)

            if not params:
                continue

            if "flag" not in params:
                continue

            worker = mp.Process(target=self.launch_user,
                                args=(user, params))

            worker.start()
            # worker.join()

        queue.join()

    # Действие для процесса
    def launch_user(self, user, params):
        # Очищаем лог, если перезапускаем вручную
        if self.silent:
            with open("logs/" + user + ".log", 'w') as target:
                target.truncate()

        while True:
            bot = ChatWarsFarmBot(user, params, self.silent)

            # Если выводим в консоль, начинаем без задержки
            if self.silent:
                bot.sleep(random.random()*30, "Я очень люблю спать", False)

            # Перезагружаем и откладываем все действия
            if self.reboots[user]:
                for location in bot.locations:
                    bot.postpone_location(location)

                bot.client.send_text(bot.group, "Перепросыпаюсь")

            else:
                bot.send_penguin()
                bot.client.send_text(bot.group, "Просыпаюсь")

            # Поехали
            try:
                bot.spam()

            except OSError as err:
                bot.log("Ошибка:", err.__class__.__name__)
                time.sleep(60*random.random())

            except telethon.RPCError:
                bot.log("Ошибка РПЦ, посплю немного")
                time.sleep(60*random.random())

            except telethon.BadMessageError:
                bot.log("Плохое сообщение, немного посплю")
                time.sleep(120 + 60*random.random())

            except Exception as err:
                if not self.avoid_errors and not self.silent:
                    bot.client.send_text(bot.group, "Помогите!")
                    time.sleep(5)
                    bot.client.send_text(bot.group, str(err))

                else:
                    raise e

                bot.log("!! Ошибка:", str(err))
                break

            self.reboots[user] = True


if __name__ == '__main__':
    MAIN = Main()
    MAIN.launch()
