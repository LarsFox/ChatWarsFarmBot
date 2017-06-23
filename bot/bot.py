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
from bot.data import CHATS, WAR, \
                     ATTACK, DEFEND, HERO, \
                     COOLDOWN, \
                     CARAVAN, LEVEL_UP, PLUS_ONE, EQUIP_ITEM

from bot.helpers import Logger, get_fight_command
from bot.updater import Updater
from modules.locations import LOCATIONS
from sessions import ENTER_CAVE, SUPERGROUP_ID


class ChatWarsFarmBot(object):
    """ Бот для каждой сессии """
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

        # Собираем данные
        self.data = data
        self.locations = LOCATIONS

        # Добавляем модуль с запросами
        self.updater = Updater(
            self.client,
            self.logger,
            self.chats,
            self.data['level']
        )

        # Делаем первый запрос бота
        self.mid, self.message = self.updater.bot_message

        # Если запускаем в Виндоуз, переименовываем окно
        if os.name == 'nt':
            os.system("title " + user + " as ChatWarsFarmBot")

        # Устанавливаем важные параметры
        self.data['exhaust'] = time.time()  # время отдышаться
        self.data['order'] = None           # последний приказ в Супергруппе
        self.data['sent_defend'] = False    # отправляем 1 раз до и после боя
        self.data['flag'] = WAR[self.data['flag']]  # флаг в виде смайлика

        # Поехали!
        self.logger.log("Сеанс {} открыт".format(user))

    # Системные функции

    def start(self):
        """ Основное древо запусков функций """
        while True:
            # Бой в 12:00. 11:00 в игре == 8:00 UTC+0
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
                    self.logger.sleep(45, "~Минутку посплю после приказа", False)

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
                if time.time() > self.data['exhaust']:
                    self.send_locations()
                    self.logger.sleep(105, "~А теперь посплю пару минут", False)

                else:
                    self.logger.sleep(105, "~Сил нет, сплю две минуты", False)

        return True

    def update(self, message=None, sleep=5):
        """
        Отправляет сообщение Боту и минуту ждет ответа
        message: сообщение к отправке
        sleep: пауза после отправки сообщения
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
        """ Обходит капчу """
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
        self.logger.sleep(10, "Десять секунд, на всякий случай жду Капчеватора")

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

    # Сокращения

    @property
    def space(self):
        """ Окончание женского рода или простой пробел """
        if self.data['girl']:
            return "а "
        return " "

    # Конец

    # Бой

    def attack(self):
        """
        Считывает приказ из Супергруппы
        Считывает его
        Надевает атакующую одежду
        """

        self.data['order'] = self.updater.order

        if self.data['order'] and self.data['order'] != self.data['flag']:
            self.hero()
            self.logger.log("Иду в атаку")

            self.update(ATTACK)

            self.logger.log("Отправляю приказ из файла")
            self.update(self.data['order'])

            self.equip("attack")

        return True

    def defend(self):
        """ Отправляет приказ к защите """
        self.hero()

        if not self.data['sent_defend']:
            if "Отдых" in self.message:
                self.logger.log("Становлюсь в защиту")
                self.update(DEFEND)

                if "будем держать оборону" in self.message:
                    self.update(self.data['flag'])

                self.data['sent_defend'] = True

        return True

    def wind(self):
        """
        Спит после боя
        Отправляет /report боту игры
        Если бот проснулся, надевает защитную одежду
        Отписывается о выполнении приказа в Супергруппу
        Забывает приказ
        """
        if not self.data['sent_defend']:
            return False

        self.update("/report")

        if "завывает" in self.message:
            return False

        if self.data['order'] is not None:
            if self.data['order'] != self.data['flag']:
                self.updater.send_group("Атаковал" + self.space + self.data['order'])
                self.equip("defend")

            else:
                self.updater.send_group("Защищал" + self.space + self.data['order'])

            self.data['order'] = None
            self.logger.log("Приказ устарел, забываю его")

        else:
            self.updater.send_group("Не увидел" + self.space + "приказ :(")

        self.data['sent_defend'] = False

        if self.data['level'] > 15:
            self.updater.send_penguin()

        return True

    def equip(self, state):
        """ Надевает указанные предметы """
        for hand in self.data["equip"].values():
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

            # Команда не требует времени на выполнение, идем дальше
            if location.instant:
                continue

            # Определяем, идем ли в пещеру
            if name == "cave":
                if self.data['level'] < ENTER_CAVE:
                    if random.random() < 0.5:
                        cave = True

            # ... и если идем в пещеру, то не идем в лес
            if name == "woods" and cave:
                continue

            # Если устали, откладываем отправку всех команд на пару часов
            if "мало единиц выносливости" in self.message:
                self.logger.log("~Выдохся, поживу без приключений пару часов")

                exhaust = time.time() + COOLDOWN + random.random() * 3600
                self.data['exhaust'] = exhaust
                return False

            # Если уже в пути, прерываем отправку команд
            if "сейчас занят другим приключением" in self.message:
                self.logger.log("А, я же не дома")
                return False

            self.logger.sleep(310, "Вернусь через 5 минут")

            self.fight()

            if random.random() < 0.4:
                self.hero()

        return True

    def hero(self):
        """
        Запрашивает профиль героя
        И прокачивает уровень, если может
        """
        self.update(HERO)

        if LEVEL_UP in self.message:
            self.logger.log("Ух-ты, новый уровень!")
            self.update(LEVEL_UP)

            if "какую характеристику ты" in self.message:
                self.update(PLUS_ONE)

            else:
                self.logger.log("Странно, где же выбор?")

        return True

    # Конец

    def caravan(self):
        """ Перехват КОРОВАНА """
        if CARAVAN in self.message:
            self.logger.log("Защищаю караван")
            self.update(CARAVAN)
            self.logger.sleep(45, "~Минутку посплю после каравана", False)

        return True

    def help_other(self):
        """ Помощь друзьям и Супергруппы """
        command = get_fight_command(self.updater.group_message)

        if command:
            self.logger.log("Иду на помощь: {}".format(command))
            self.client.send_text(self.chats["group"], "+")
            self.update(command)

        return True

    def fight(self):
        """ Отправка команды сражения с монстром """
        self.update()
        command = get_fight_command(self.message)

        if command:
            self.logger.sleep(5, "А вот и монстр! Сплю пять секунд перед дракой")
            self.client.send_text(self.chats["group"], command)
            self.update(command)

        return True

    # Конец
