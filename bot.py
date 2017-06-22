
# coding=utf-8
"""
Собственно, сам бот
"""

import datetime
import os
import random
import time


from client import TelethonClient
from data import CHATS, COMMANDS, WAR, WAR_COMMANDS, \
                 ATTACK, DEFEND, HERO, CASTLE, WOODS, CAVE, \
                 LOCATIONS, COOLDOWN, \
                 CARAVAN, FIGHT, LEVEL_UP, PLUS_ONE, EQUIP_ITEM


from sessions import ENTER_CAVE, SUPERGROUP_ID


class ChatWarsFarmBot(object):
    def __init__(self, user, params, silent=True):
        # Подключаемся к Телеграму
        self.client = TelethonClient(user, params['phone'])

        # Проверяем последние 10 диалогов
        _, entities = self.client.get_dialogs(10)

        # Создаем контакты
        self.chats = {}
        for entity in entities:
            name = CHATS.get(entity.id)

            if name:
                self.chats[name] = entity

            elif entity.id == SUPERGROUP_ID:
                self.chats['group'] = entity

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
        """ Основное древо запусков функций """
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
            self.client.send_text(self.chats["captcha_bot"], self.message)
            self.sleep(10, "Десять секунд, на всякий случай жду Капчеватора")

            _, captcha_answer = self.client.get_message(self.chats["captcha_bot"])

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
            self.client.send_text(self.chats["cw"], message)
            self.sleep(sleep, "Сплю пять секунд после отправки сообщения")

        for i in range(1, 7):
            self.last_id, self.message = self.client.get_message(self.chats["cw"])

            if self.old_id == self.last_id:
                self.sleep(10, "Жду сообщение: {}/6".format(i))

            else:
                self.old_id = self.last_id
                break

        return self.check_captcha()

    def stop(self):
        """ Убиваем процесс """
        self.client.send_text(self.chats["group"], "У меня тут проблема")
        self.client.send_text(self.chats["group"], self.message)
        sys.exit()  # (!) проверить, выключаются ли все боты или один

    # Конец

    # Сокращения

    @property
    def bot_message(self):
        """ Последнее сообщение от бота игры """
        _, message = self.client.get_message(self.chats["cw"])
        return message

    @property
    def group_message(self):
        """ Последнее сообщение от Супергруппы """
        _, message = self.client.get_message(self.chats["group"], False)
        return message

    def send_penguin(self):
        """ Отправляем инвентарь Пингвину """
        if self.level < 15:
            return False

        self.client.send_text(self.chats["trade_bot"], "/start")
        self.sleep(3, "Отправляю инвентарь пингвину")

        _, message = self.client.get_message(self.chats["trade_bot"])
        self.client.send_text(self.chats["penguin"], message)
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
                            self.chats["group"],
                            "Атаковал" + self.la + " {}".format(self.order)
                        )
                        self.equip("defend")

                    else:
                        self.client.send_text(
                            self.chats["group"],
                            "Защищал" + self.la + " {}".format(self.order)
                        )

                    self.log("Приказ устарел, забываю его")
                    self.order = None

                else:
                    self.client.send_text(
                        self.chats["group"],
                        "Не увидел" + self.la + " приказ :("
                    )

                self.sent_defend = False
                self.send_penguin()

        return True

    def equip(self, state):
        """ Надеваем указанные предметы """
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
        """ Откладываем поход в локацию """
        delta = random.random() * 1200 + 900
        location.after = time.time() + delta

        self.log("Отправлю {} через {:.3f} минут".format(
            location.console,
            delta / 60
        ))

        return True

    def send_locations(self):
        """ Отправляемся во все локации """
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
        """ Запрос рейтинга замков """
        return self.pay_visit("/worldtop")

    def report(self, prob=0.7):
        """ Запрос отчета о битве """
        return self.pay_visit("/report", prob)

    def commands(self):
        """ Запрос случайной команды """
        return self.pay_visit(random.choice(COMMANDS))

    def castle(self):
        """ Поход в замок """
        return self.pay_visit(CASTLE)

    def pay_visit(self, command, prob=0.7):
        """ Отправка команды без задержки """
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
        """ Выбор между лесом и пещерой """
        if self.level >= ENTER_CAVE:
            if random.random() < prob:
                return self.travel(CAVE)
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
        """ Перехват КОРОВАНА """
        self.message = self.bot_message
        if CARAVAN in self.message:
            self.log("Защищаю караван")
            self.update_bot(CARAVAN)
            self.sleep(45, "~Минутку посплю после каравана", False)

        return True

    def help_other(self):
        """ Помощь друзьям и Супергруппы """
        command = self.extract_fight_command(self.group_message)

        if command:
            self.log("Иду на помощь: {}".format(command))
            self.client.send_text(self.chats["group"], "+")
            self.update_bot(command)

        return True

    def fight(self):
        """ Отправка команды сражения с монстром """
        self.message = self.bot_message
        command = self.extract_fight_command(self.message)

        if command:
            self.sleep(5, "А вот и монстр! Сплю пять секунд перед дракой")
            self.client.send_text(self.chats["group"], command)
            self.update_bot(command)

        return True

    # Конец
