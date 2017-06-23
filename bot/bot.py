# coding=utf-8
"""
Собственно, сам бот
"""

import datetime
import os
import random
import time
import sys


from bot.client import TelethonClient
from bot.data import CHATS, WAR, COOLDOWN, \
                     ATTACK, DEFEND, HERO, \
                     CARAVAN, LEVEL_UP, PLUS_ONE, EQUIP_ITEM

from bot.helpers import Logger, get_fight_command
from bot.updater import Updater
from modules.locations import LOCATIONS
from sessions import ENTER_CAVE, SUPERGROUP_ID


class ChatWarsFarmBot(object):
    """ Объект бота для каждой сессии """

    # pylint: disable=too-many-instance-attributes

    def __init__(self, user, data, silent=True):
        # Подключаемся к Телеграму
        self.client = TelethonClient(user, data['phone'])

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

        # Определяем тип вывода
        if silent:
            log_file = 'logs/' + user + '.log'
        else:
            log_file = None

        self.logger = Logger(user, log_file)

        # Устанавливаем важные параметры
        self.exhaust = time.time()  # время отдышаться
        self.order = None           # последний приказ в Супергруппе
        self.sent_defend = False    # отправляем 1 раз до и после боя

        self.equipment = data['equip']  # обмундирование
        self.flag = WAR[data['flag']]   # флаг в виде смайлика
        self.level = data['level']      # уровень героя

        # Создаем локации
        self.locations = LOCATIONS

        # Добавляем модуль с запросами
        self.updater = Updater(
            self.client,
            self.logger,
            self.chats,
            self.level
        )

        # Делаем первый запрос бота
        self.mid, self.message = self.updater.bot_message

        # Если запускаем в Виндоуз, переименовываем окно
        if os.name == 'nt':
            os.system("title " + user + " as ChatWarsFarmBot")

        if data['girl']:
            space = 'а '
        else:
            space = ' '

        self.verbs = {
            ATTACK: "Атаковал" + space,
            DEFEND: "Защищал" + space,
            "notice": "Не увидел" + space
        }

        # Поехали!
        self.logger.log("Сеанс {} открыт".format(user))

    # Системные функции

    def start(self):
        """ Запускает бота """
        while True:
            # Бой каждые четыре часа. Час перед утренним боем — 8:00 UTC+0
            now = datetime.datetime.utcnow()

            # Собираем сообщение
            self.mid, self.message = self.updater.bot_message

            # Защищаем КОРОВАНЫ
            self.caravan()

            # Смотрим, кому можем помочь
            # Есть вероятность, что никто не поможет
            self.help_other()

            # (!) переписать для ранних приказов
            # С 47-й минуты ничего не делаем
            if (now.hour) % 4 == 0 and now.minute >= 47:
                # На 59-й идем в атаку
                if now.minute >= 59 and now.second >= 25:
                    self.attack()
                    self.logger.sleep(45, "~Минутка сна после приказа", False)

                # На 58-й уменьшаем время ожидания
                elif now.minute >= 58:
                    self.logger.sleep(5, "Подбираюсь к отправке приказа")

                # С 54-й спим по минуте и заранее становимся в защиту
                elif now.minute >= 54:
                    self.defend()
                    self.logger.sleep(60, "Сплю, пока битва близко")

                # С 47-й спим по две минуты
                else:
                    self.logger.sleep(120, "Время перед битвой, сижу тихо")

            # До 7-й минуты ничего не делаем
            elif (now.hour-1) % 4 == 0 and now.minute < 7:
                self.logger.sleep(180, "Жду, пока завывает ветер")
                self.wind()

            # В остальное время отправляем команды
            else:
                if time.time() > self.exhaust:
                    self.send_locations()
                    self.logger.sleep(105, "~Теперь посплю пару минут", False)

                else:
                    self.logger.sleep(105, "~Сил нет, сплю две минуты", False)

        return True

    def update(self, message=None, sleep=5):
        """
        Отправляет сообщение Боту и минуту ждет ответа
        message: строка, сообщение к отправке
        sleep: число секунд — пауза после отправки сообщения
        """
        if message:
            self.client.send_text(self.chats["cw"], message)
            self.logger.sleep(sleep)

        for i in range(1, 7):
            mid, message = self.updater.bot_message

            if self.mid == mid:
                self.logger.sleep(10, "Жду сообщение: {}/6".format(i))

            else:
                self.mid, self.message = mid, message
                break

        return self.captcha()

    def captcha(self):
        """ Обходит капчу и останавливает бота, если не обходит """
        if "На выходе из замка" not in self.message:
            return True

        if "Не умничай" in self.message:
            self.stop()

        elif "Не шути" in self.message:
            self.stop()

        elif "вспотел" in self.message:
            self.stop()

        self.logger.log("Капча!")
        self.client.send_text(self.chats["captcha_bot"], self.message)
        self.logger.sleep(10, "Десять секунд, жду Капчеватора")

        _, captcha_answer = self.client.get_message(self.chats["captcha_bot"])

        if "Не распознано" in captcha_answer:
            self.stop()

        self.logger.log("Отдаю ответ")
        self.update(captcha_answer)

        return True

    def stop(self):
        """ Останавливает бота """
        self.client.send_text(self.chats["group"], "У меня тут проблема")
        self.client.send_text(self.chats["group"], self.message)
        sys.exit()  # (!) проверить, выключаются ли все боты или один

    # Конец

    # Бой

    def attack(self):
        """
        Считывает приказ из Супергруппы.
        Затем надевает атакующую одежду и отправляется в атаку
        """

        self.order = self.updater.order

        if self.order and self.order != self.flag:
            self.hero()
            self.logger.log("Иду в атаку")

            self.update(ATTACK)

            self.logger.log("Отправляю приказ из файла")
            self.update(self.order)

            self.equip("attack")

        return True

    def defend(self):
        """ Отправляет приказ к защите """
        self.hero()

        if not self.sent_defend:
            if "Отдых" in self.message:
                self.logger.log("Становлюсь в защиту")
                self.update(DEFEND)

                if "будем держать оборону" in self.message:
                    self.update(self.flag)

                self.sent_defend = True

        return True

    def wind(self):
        """
        Спит после боя, и запрашивает отчет о битве.
        Если бот проснулся, надевает защитную одежду.
        Отписывается о выполнении приказа в Супергруппу и забывает приказ
        """
        # Отчет уже спрашивали, пропускаем
        if not self.sent_defend:
            return False

        # Спрашиваем отчет
        self.update("/report")

        # Бот еще не проснулся, ждем
        if "завывает" in self.message:
            return False

        # Если был потерян предмет, оповещаем Супергруппу о беде
        if "Вы потеряли" in self.message:
            self.updater.send_group(self.message)

        # Отчитываемся о приказе
        if self.order is not None:
            if self.order != self.flag:
                self.updater.send_group(self.verbs[ATTACK] + self.order)
                self.equip("defend")

            else:
                self.updater.send_group(self.verbs[DEFEND] + self.order)

            self.order = None
            self.logger.log("Приказ устарел, забываю его")

        else:
            self.updater.send_group(self.verbs["notice"] + "приказ :(")

        self.sent_defend = False

        # С 15-го уровня работает обмен, узнаем информацию
        if self.level > 15:
            self.updater.send_penguin()

        return True

    def equip(self, state):
        """ Надевает указанные предметы """
        for hand in self.equipment.values():
            if len(hand) == 2:
                item = EQUIP_ITEM.format(hand[state])
                self.logger.log("Надеваю: {}".format(item))
                self.update(item, sleep=3)

        self.logger.log("Завершаю команду {}".format(state))
        return True

    # Конец

    # Мирное время

    def send_locations(self):
        """ Отправляется во все локации """
        cave = False
        for name, location in self.locations.items():
            # Пропускаем, если время идти в локацию еще не пришло
            if time.time() - location.after < 0:
                continue

            # Пропускаем, если шанс говорит не идти
            if not location.travel():
                self.logger.sleep(10, "Пропускаю " + location.console)
                continue

            # Идем в локацию
            self.logger.log("Отправляю " + location.console)
            self.update(location.emoji)

            # Откладываем следующий поход
            self.logger.log("Следующий {} через {:.3f} минут".format(
                location.console,
                location.postpone()
            ))

            # Команда не требует затрат времени, выполняем следующую
            if location.instant:
                continue

            # Определяем, идем ли в пещеру
            if name == "cave":
                if self.level > ENTER_CAVE:
                    if random.random() < 0.5:
                        cave = True

            # ... и если идем в пещеру, то не идем в лес
            if name == "woods" and cave:
                continue

            # Если устали, откладываем отправку всех команд
            if "мало единиц выносливости" in self.message:
                self.logger.log("~Выдохся, поживу без приключений пару часов")

                exhaust = time.time() + COOLDOWN + random.random() * 3600
                self.exhaust = exhaust
                return False

            # Если уже в пути, прерываем отправку команд
            if "сейчас занят другим приключением" in self.message:
                self.logger.log("А, я же не дома")
                return False

            self.logger.sleep(310, "Вернусь через 5 минут")

            # По возвращении деремся с монстром, если он есть
            self.fight()

            # И ради интереса запрашиваем свой профиль
            if random.random() < 0.4:
                self.hero()

        return True

    def hero(self):
        """ Запрашивает профиль героя и увеличивает уровень """
        self.update(HERO)

        if LEVEL_UP in self.message:
            self.logger.log("Ух-ты, новый уровень!")
            self.update(LEVEL_UP)

            if "какую характеристику ты" in self.message:
                self.update(PLUS_ONE)

            else:
                self.logger.log("Странно, где же выбор?")

        return True

    def caravan(self):
        """ Перехватывает КОРОВАН """
        if CARAVAN in self.message:
            self.logger.log("Защищаю караван")
            self.update(CARAVAN)
            self.logger.sleep(45, "~Минутку посплю после каравана", False)

        return True

    def help_other(self):
        """ Помогает друзьям из Супергруппы """
        command = get_fight_command(self.updater.group_message)

        if command:
            self.logger.log("Иду на помощь: {}".format(command))
            self.client.send_text(self.chats["group"], "+")
            self.update(command)

        return True

    def fight(self):
        """ Отправляет команды сражения с монстром """
        self.update()
        command = get_fight_command(self.message)

        if command:
            self.logger.sleep(5, "Монстр! Сплю пять секунд перед дракой")
            self.client.send_text(self.chats["group"], command)
            self.update(command)

        return True

    # Конец
