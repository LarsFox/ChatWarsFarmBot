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
                     ATTACK, DEFEND, VERBS, REGROUP, HERO, \
                     CARAVAN, LEVEL_UP, PLUS_ONE, EQUIP_ITEM

from bot.helpers import Logger, get_fight_command
from bot.updater import Updater
from modules.locations import LOCATIONS
from sessions import CAVE_LEVEL, CAVE_CHANCE, SUPERGROUP_ID


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
        self.status = None          # статус бота до и после битвы

        self.equipment = data['equip']  # обмундирование
        self.girl = data['girl']
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

            # С 47-й минуты ничего не делаем
            if (now.hour) % 4 == 0 and now.minute >= 47:
                self.order = self.updater.order

                # Если стоим в защите, пробуем идти в атаку на основе приказа
                if self.status == DEFEND:
                    self.attack()

                # Если отдыхаем, идем в защиту
                elif self.status is None:
                    self.defend()

                # Если получили приказ отступать, становимся в защиту
                if self.order == REGROUP:
                    self.defend()
                    self.equip(DEFEND)

                # C 59-й обновляем приказ очень часто
                if now.minute >= 59 and now.second >= 15:
                    self.logger.sleep(5, "Дремлю, пока битва близко")

                # C 58-й чаще обновляем приказ
                elif now.minute >= 58:
                    self.logger.sleep(15, "Дремлю, пока битва близко")

                # С 54-й спим по минуте
                elif now.minute >= 54:
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
        """ Надевает атакующую одежду и отправляется в атаку """
        if self.order and self.order != self.flag:
            self.hero()
            self.logger.log("Иду в атаку")
            self.update(ATTACK)
            self.update(self.order)
            self.equip(ATTACK)
            self.status = ATTACK

        return True

    def defend(self):
        """ Отправляет приказ к защите """
        self.hero()
        self.logger.log("Становлюсь в защиту")
        self.update(DEFEND)

        if "будем держать оборону" in self.message:
            self.update(self.flag)

        self.status = DEFEND

        return True

    def wind(self):
        """
        Спит после боя, и запрашивает отчет о битве.
        Если бот проснулся, надевает защитную одежду и забывает приказ
        """
        # Отчет уже спрашивали, пропускаем
        if not self.status:
            return False

        # Спрашиваем отчет
        self.update("/report")

        # Бот игры еще не проснулся, пропускаем
        if "завывает" in self.message:
            return False

        # Оповещаем Супергруппу о полученном приказе
        self.updater.send_group(VERBS[self.girl][self.status] + self.order)

        # Если был потерян предмет, оповещаем Супергруппу о беде
        if "Вы потеряли" in self.message:
            self.updater.send_group(self.message)

        # Надеваем защитную одежду для лучшего сбора, если шли в атаку
        if self.status == ATTACK:
            self.equip(DEFEND)

        # Обновляем информацию у Пингвина
        self.updater.send_penguin()

        # Забываем боевой статус и приказ
        self.order = None
        self.status = None

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
        for location in self.locations:
            # Пропускаем, если время идти в локацию еще не пришло
            if time.time() - location.after < 0:
                continue

            # Пропускаем, если шанс говорит не идти
            if not location.travel():
                self.logger.sleep(10, "Пропускаю " + location.console)
                continue

            # Определяем, идем ли в пещеру
            if location.console == "поход в пещеру":
                if self.level < CAVE_LEVEL or random.random() > CAVE_CHANCE:
                    continue

                cave = True

            # ... и если идем в пещеру, то не идем в лес
            if location.console == "поход в лес" and cave:
                continue

            # Отправляем сообщение с локацией
            self.logger.log("Отправляю " + location.console)
            self.update(location.emoji)

            # Откладываем следующий поход
            self.logger.log("Следующий {} через {:.3f} минут".format(
                location.console,
                location.postpone()
            ))

            # Локация не требует затрат времени, пропускаем задержку
            if location.instant:
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
