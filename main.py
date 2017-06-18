# coding=utf-8

import datetime
import multiprocessing as mp
import os
import random
import time
import sys

from telethon import RPCError, TelegramClient
from telethon.errors import *

from data import *
from sessions import *


class ChatWarsFarmBot(TelegramClient):
    def __init__(self, user, params, silent=True):
        # Собираем данные
        user_phone = params['phone']
        flag = params['flag']

        self.user = user
        self.silent = silent

        self.flag = WAR[flag]               # Флаг из sessions
        self.equipment = params["equip"]    # Снаряжение из sessions
        self.locations = LOCATIONS          # Локации из data

        # Выбираем формат вывода данных
        if self.silent:
            self.log_file = "logs/" + self.user + ".log"

            with open(self.log_file, 'w') as target:
                target.truncate()

        # Если запускаем в Виндоуз, переименовываем окно
        if os.name == 'nt':
            os.system("title " + self.user + " as ChatWarsFarmBot")

        # Создаем файл сессии
        super().__init__("sessions/" + self.user, API_ID, API_HASH)

        # ... и подключаемся к Телеграму
        self.connect()

        # Если ТГ просит код, вводим его и умираем
        # Если много аккаунтов, запускаем через -l
        if not self.is_user_authorized():
            self.log('Первый запуск. Запрашиваю код...')
            self.send_code_request(user_phone)

            code_ok = False
            while not code_ok:
                code = input('Введите полученный в Телеграме код: ')
                code_ok = self.sign_in(user_phone, code)

            sys.exit("{} код получил, перезапускай.".format(self.user))

        # Не держим больше 10 диалогов
        dialogs, entities = self.get_dialogs(10)

        # Создаем контакты по id из data
        for entity in entities:
            important = IMPORTANT.get(entity.id)

            if important:
                setattr(self, important, entity)

        # Поехали!
        self.log("Сеанс {} под флагом {} открыт".format(self.user, flag))

    def spam(self):
        self.spamming = True

        self.exhaust = time.time()       # время отдышаться

        self.message = self.bot_message  # последнее сообщение от Бота
        self.old_id = 0                  # и его номер

        self.order = None                # последний приказ в Супергруппе
        self.sent_defend = False         # отправляем 1 раз до и после боя

        while self.spamming:
            # Бой в 12:00. 11:00 в игре == 8:00 UTC+0
            now = datetime.datetime.utcnow()

            if not self.check_captcha():
                self.stop()

            # Защищаем КОРОВАНЫ
            self.caravan()

            # Сначала смотрим, кому можем помочь
            # Есть вероятность, что никто не поможет
            self.help_other()

            # С 47-й минуты ничего не делаем
            if (now.hour) % 4 == 0 and now.minute >= 47:
                # На 59-й идем в атаку
                if now.minute >= 59 and now.second >= 25:
                    self.attack()
                    self.sleep(45, "~Минутку посплю после приказа", False)

                # На 57-й идем в защиту
                elif now.minute >= 57:
                    self.defend()

                    self.sleep(5, "Подбираюсь к отправке приказа")

                # С 54-й спим по минуте
                elif now.minute >= 54:
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
                    self.sleep(105, "~Все сделал, посплю пару минут", False)

                else:
                    self.sleep(105, "~Сил нет, сплю две минуты", False)

        return True

    # Системные функции

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

    def sleep(self, z, message=None, exact=True):
        """ Спим и логгируем """
        if not exact:
            z += random.random() * 30

        if message:
            if "{" in message:
                self.log(message.format(z/60))

            else:
                self.log(message)

        else:
            self.log("Ложусь спать на {:.3f} минут".format(z/60))

        time.sleep(z)

        return True

    def send_text(self, entity, message):
        """ Отправляем сообщение определенному адресату-entity """
        self.send_message(entity, message, markdown=True, no_web_page=True)

    def get_message(self, entity, repeat=True):
        """
        Собираем последнее сообщение
        entity: адресат-entity
        repeat: повторяем сбор, пока не получим сообщение от адресата
        Возвращаем номер сообщения и его содержимое
        """
        num, messages, senders = self.get_message_history(entity, 1)

        if repeat:
            for x in range(15):
                if senders[0].id == entity.id:
                    break

                num, messages, senders = self.get_message_history(entity, 1)
                self.sleep(3, "Три секунды, жду новое сообщение")

        message = messages[0]
        sender = senders[0]

        # self.log(message)

        if getattr(message, 'media', None):
            content = '<{}> {}'.format(
                message.media.__class__.__name__,
                getattr(message.media, 'caption', ''))

        elif hasattr(message, 'message'):
            content = message.message

        elif hasattr(message, 'action'):
            content = message.action.encode('utf-8')

        else:
            content = message.__class__.__name__

        return message.id, content

    def check_captcha(self):
        """ Проверяем капчу от бота """
        if "На выходе из замка" in self.message:
            self.log("Обнаружил капчу")
            self.send_text(self.captcha_bot, self.message)
            self.sleep(10, "Десять секунд, на всякий случай жду Капчеватора")

            captcha_answer = self.get_message(self.captcha_bot)[1]

            if "Не распознано" not in captcha_answer:
                self.log("Отдаю ответ")
                self.update_bot(captcha_answer)

                if "Ты отправился" in self.message:
                    self.log("Отправился и попутно обоссал капчу")
                    return True

                elif "Ты ответил правильно" in self.message:
                    self.log("Слишком просто")
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
            self.send_text(self.cw, message)
            self.sleep(sleep, "Сплю пять секунд после отправки сообщения")

        for i in range(1, 7):
            self.last_id, self.message = self.get_message(self.cw)

            if self.old_id == self.last_id:
                self.sleep(10, "Жду сообщение: {}/6".format(i))

            else:
                self.old_id = self.last_id
                break

        return self.check_captcha()

    def stop(self, reason="капча"):
        """ Убиваем процесс """
        self.send_text(self.group, "У меня тут проблема")
        self.send_text(self.group, self.message)
        sys.exit()  # (!) проверить, выключаются ли все боты или один

    # Конец

    # Сокращения

    @property
    def bot_message(self):
        """ Последнее сообщение от бота игры """
        return self.get_message(self.cw)[1]

    @property
    def group_message(self):
        """ Последнее сообщение от Супергруппы """
        return self.get_message(self.group, False)[1]

    def send_penguin(self):
        """ Отправляем инвентарь Пингвину """
        self.send_text(self.trade_bot, "/start")
        self.sleep(3, "Отправляю инвентарь пингвину")
        self.send_text(self.penguin, self.get_message(self.trade_bot)[1])
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

                self.have_asked_report = False
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
                        self.send_text(
                            self.group,
                            "Атаковал {}".format(self.order)
                        )
                        self.equip("defend")

                    else:
                        self.send_text(
                            self.group,
                            "Защищал {}".format(self.order)
                        )

                    self.log("Приказ устарел, забываю его")
                    self.order = None

                else:
                    self.send_text(self.group, "Не увидел приказ :(")

                self.sent_defend = False
                self.send_penguin()

        return True

    def equip(self, state):
        for hand, items in self.equipment.items():
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
                self.log("Странно, я не получил выбор")

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

        else:
            return self.sleep(10, "Ничего не отправляю, просто сплю")


    # Конец

    # Пятиминутные действия (go)

    def arena(self):
        # (!)
        return True

    def build(self):
        # (!)
        return True

    def woods(self):
        return self.go(WOODS)

    def cave(self):
        # (!) с 30-го уровня
        return self.go(CAVE)

    def go(self, message):
        """
        Отправляет команду боту
        Откладывает все команды, если видит усталость
        Сражается, если видит монстра
        После запрашивает профиль героя, мол, изменилось ли что?
        """
        go = self.update_bot(message)

        if "мало единиц выносливости" in self.message:
            self.log("~Выдохся, откладываю на два часа")
            self.exhaust = time.time() + COOLDOWN + random.random() * 3600
            return False

        if "сейчас занят другим приключением" in self.message:
            self.log("А, забыл, что я занят")
            return False

        if go:
            self.sleep(310, "Отправился, сплю 5 минут")

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
            c = message.index(FIGHT)
            return message[c:c+27]

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
            self.send_text(self.group, "+")
            self.update_bot(command)

        return True

    def fight(self):
        self.message = self.bot_message
        command = self.extract_fight_command(self.message)

        if command:
            self.sleep(5, "Увидел монстра, сплю пять секунд перед дракой")
            self.send_text(self.group, command)
            self.update_bot(command)

        return True

    # Конец


class Main(object):
    def __init__(self):
        """
        -s: логгируем в файл или в консоль
        -t: запускаем .test() в процессе первого пользователя и выводим в консо
        -e: игнорирует все ошибки и спамит о них в Супергруппу
        -l: проверяем логин и вводим телефон (только для одного пользователя)
        -c: показываем код в запущенном ТГ (только для одного пользователя)
        -r: «перезапуск»: все действия откладываются, чтобы не спамить

        все остальные аргументы будут приняты как имена сессии
        """
        self.silent = "-s" in sys.argv
        self.test = "-t" in sys.argv
        self.avoid_errors = "-e" in sys.argv
        self.login = "-l" in sys.argv
        self.code = "-c" in sys.argv

        self.users = [
            arg.capitalize() for arg in sys.argv[1:]
            if "-" not in arg
        ]

        if len(self.users) == 0:
            sys.exit("Запуск без пользователей невозможен")

        if " " in self.users[0]:
            self.users = self.users[0].split()

        reboot = "-r" in sys.argv
        self.reboots = {user: reboot for user in self.users}
        self.pipes = {user: 0 for user in self.users}

    def test(self):
        pass

    def launch(self):
        # -l
        if self.login:
            if len(self.users) > 1:
                sys.exit("Логин возможен только для одного пользователя")

            user = self.users[0]
            params = SESSIONS.get(user)
            tg = ChatWarsFarmBot(user, params, self.silent)
            sys.exit("Код уже был введен!")

        # -c
        if self.code:
            if len(self.users) > 1:
                sys.exit("Могу показать код только у одного пользователя")

            user = self.users[0]
            params = SESSIONS.get(user)
            tg = ChatWarsFarmBot(user, params, self.silent)
            sys.exit(tg.get_message(tg.telegram)[1][:23])

        # -t
        if self.test:
            self.silent = True
            self.avoid_errors = True
            user = self.users[0]
            params = SESSIONS.get(user)

            tg = ChatWarsFarmBot(user, params, self.silent)
            self.test()
            sys.exit("Завершен.")

        # Остальной набор
        queue = mp.JoinableQueue()

        for i, user in enumerate(self.users):
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
        while True:
            tg = ChatWarsFarmBot(user, params, self.silent)

            # Если выводим в консоль, начинаем без задержки
            if self.silent:
                tg.sleep(random.random()*30, "Я очень люблю спать", False)

            # Перезагружаем и откладываем все действия
            if self.reboots[user]:
                for location in tg.locations:
                    tg.postpone_location(location)

                tg.send_text(tg.group, "Перепросыпаюсь")

            else:
                tg.send_penguin()
                tg.send_text(tg.group, "Просыпаюсь")

            # Поехали
            try:
                tg.spam()

            except (ConnectionAbortedError,
                    ConnectionResetError,
                    TimeoutError) as e:
                tg.log("Ошибка:", e.__class__.__name__)
                time.sleep(60*random.random())

            except BrokenPipeError as e:
                tg.log("Труба потекла")
                self.pipes[user] += 1

                if self.pipes[i] == 10:
                    tg.log("(!) Затопила труба")

                if self.pipes[i] == 100:
                    break

            except RPCError:
                tg.log("Ошибка РПЦ, посплю немного")
                time.sleep(60*random.random())

            except BadMessageError:
                tg.log("Плохое сообщение, немного посплю")
                time.sleep(120 + 60*random.random())

            except Exception as e:
                if not self.avoid_errors and not self.silent:
                    tg.send_text(tg.group, "Капитан, у меня проблемы!")
                    time.sleep(5)
                    tg.send_text(tg.group, str(e))

                else:
                    raise e

                tg.log("(!) Ошибка:", str(e))
                break

            self.reboots[user] = True


if __name__ == '__main__':
    l = Main()
    l.launch()
