# coding=utf-8
"""
Собственно, сам бот
"""

import datetime
import os
import random
import time


from bot.client import TelethonClient
from bot.data import (
    COOLDOWN, HERO, HELLO, SENDING, MONSTER_COOLDOWN,
    ATTACK, DEFEND, VICTORIES, ALLY, VERBS, HANDS,
    REGROUP, CARAVAN, LEVEL_UP, PLUS_ONE, EQUIP_ITEM, QUESTS, SHORE)

from bot.logger import Logger
from bot.updater import Updater
from modules.helpers import (
    get_fight_command, go_wasteland, get_level, get_flag, count_help)

from modules.locations import LOCATIONS


class ChatWarsFarmBot(object):
    """ Объект бота для каждой сессии """

    # pylint: disable=too-many-instance-attributes

    def __init__(self, user, data, silent=True):
        # Если выводим в лог, очищаем его и начинаем с задержкой
        if silent:
            time.sleep(random.random() * 30)
            log_file = 'logs/' + user + '.log'
            with open(log_file, 'w') as target:
                target.truncate()

        else:
            log_file = None

        # Добавляем модули
        self.client = TelethonClient(user, data['phone'])
        self.logger = Logger(user, log_file, data['girl'])
        self.updater = Updater(self.client, self.logger)

        # Устанавливаем важные параметры
        self.exhaust = time.time()         # время до следующей передышки
        self.monster = time.time()         # время до сражения с монстрами
        self.order = None                  # приказ из Супергруппы
        self.status = None                 # статус бота до и после битвы
        self.locations = LOCATIONS.copy()  # все локации

        # Флаг, уровень и обмундирование определим позднее
        self.flag = None
        self.level = 0
        self.equipment = {}

        # Если запускаем в Виндоуз, переименовываем окно
        if os.name == 'nt':
            os.system("title " + user + " as ChatWarsFarmBot")

        # Поехали!
        self.logger.log("Сеанс {} открыт".format(user))

    def connect(self):
        """ Подключается к Телеграму и обновляет параметры """
        # Подключаемся и вызываем код
        self.client.connect_with_code()

        # Собираем важные параметры
        self.updater.update_chats()

        # Определяем флаг и уровень
        updated = self.updater.update("/hero")
        while not updated or VICTORIES not in self.updater.message:
            self.logger.sleep(300, "Не могу проснуться, посплю еще немного!")
            updated = self.updater.update("/hero")

        self.flag = get_flag(self.updater.message)     # флаг в виде смайлика
        self.level = get_level(self.updater.message)   # уровень героя
        self.equipment = self.updater.equipment

        # Отправляем сообщение о пробуждении
        self.updater.send_group(HELLO.format(self.flag, self.level))

    # Системные функции

    def start(self):
        """ Запускает бота """
        while True:
            # Бой каждые четыре часа. Час перед утренним боем — 8:00 UTC+0
            now = datetime.datetime.utcnow()

            # Защищаем КОРОВАНЫ
            self.caravan()

            # Смотрим, кому можем помочь
            # Есть вероятность, что никто не поможет
            self.help_other()

            # С 47-й минуты готовимся к бою
            if (now.hour) % 4 == 0 and now.minute >= 47:
                self.battle()

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

            # До 15-й минуты ничего не делаем, ждем отчет
            elif (now.hour-1) % 4 == 0 and now.minute < 15:
                self.logger.sleep(420, "Жду, пока завывает ветер")
                self.wind()

            # В остальное время отправляем команды
            else:
                if time.time() > self.exhaust:
                    self.send_locations()
                    self.logger.sleep(105, "~Теперь посплю пару минут", False)

                else:
                    self.logger.sleep(105, "~Сил нет, сплю две минуты", False)

            # self.updater.read_all_messages()

        return True

    # Конец

    # Бой

    def battle(self):
        """ Готовится к битве в зависимости от приказа """
        # Приказы игнорируются при защите союзника или атаке
        order = self.updater.order

        # Если получили приказ отступать, становимся в защиту
        if order == REGROUP:
            self.defend()

            if self.status == ATTACK:
                self.equip(DEFEND)

        # Если отдыхаем, идем в защиту
        elif self.status is None:
            self.defend()

        # Если стоим в защите, пробуем идти в атаку на основе приказа
        elif self.status == DEFEND:
            self.attack(order)

        return True

    def attack(self, order):
        """
        Надевает атакующую одежду и отправляется в атаку
        order: смайлик флага, который отправится боту
        """
        if order and order != self.flag:
            self.hero(True)
            self.logger.log("Иду в атаку")

            if not self.updater.update(ATTACK, 2, wind="поход в атаку"):
                return False

            if not self.updater.update(order, 2, wind="приказ к атаке"):
                return False

            # Нападение на союзника! Сидим дома
            if "защите" in self.updater.message:
                self.logger.log("Не могу атаковать союзника")

                # Форт остаемся защищать, а вот союзников не защищаем, ну их
                if "форт" in order:
                    self.equip(DEFEND)
                else:
                    self.defend()

                self.status = ALLY  # не защита, но и атаковать не надо

            # Атака! Одеваемся и выходим к бою
            else:
                self.equip(ATTACK)
                self.status = ATTACK
                self.order = order

        return True

    def defend(self):
        """ Надевает одежду для сбора и становится в защиту """
        self.hero(True)
        self.logger.log("Становлюсь в защиту")

        if not self.updater.update(DEFEND, 2, wind="поход в защиту"):
            return False

        if "будем держать оборону" in self.updater.message:
            if not self.updater.update(self.flag, 2, wind="приказ к защите"):
                return False

        self.order = self.flag
        self.status = DEFEND

        return True

    def wind(self):
        """
        Спит после боя, и запрашивает отчет о битве.
        Если бот проснулся, надевает защитную одежду и забывает приказ
        """
        # Отчет уже спрашивали, пропускаем
        if self.status is None:
            return False

        self.logger.sleep(random.random() * 180, "Сон рассинхронизации!")

        # Бот игры еще не проснулся, пропускаем
        if not self.updater.update("/report"):
            return False

        # Оповещаем Супергруппу о полученном приказе
        verb = VERBS[self.logger.girl][self.status]
        self.updater.send_group(verb + self.order)

        # Если был потерян или найден предмет, оповещаем Супергруппу
        if "Вы " in self.updater.message:
            self.updater.send_group(self.updater.message)

        # Обновляем инвентарь
        self.equipment = self.updater.equipment

        # Надеваем защитную одежду для лучшего сбора, если шли в атаку
        if self.status == ATTACK:
            self.equip(DEFEND)

        # Обновляем информацию у Пингвина
        if self.level >= 15:
            self.updater.send_penguin()

        # Забываем боевой статус и приказ
        self.order = None
        self.status = None

        return True

    def equip(self, state):
        """
        Надевает указанные предметы
        state: ключ, по которому будут выбраны предметы
        """
        for slot, equip in self.equipment.items():
            if len(equip) == 2:
                item = EQUIP_ITEM.format(equip[state])
                self.logger.log("Надеваю: {}".format(item))

                wind = "надеть " + HANDS[state] + slot
                if not self.updater.update(item, 3, wind):
                    return False

        self.logger.log("Завершаю команду {}".format(state))
        return True

    # Конец

    # Мирное время

    def send_locations(self):
        """ Отправляется во все локации """
        for location in self.locations:
            self.hero()

            # Пропускаем, если время идти в локацию еще не пришло
            if time.time() - location.after < 0:
                continue

            # Если требует времени, идем как приключение
            if not location.instant:
                self.updater.update(QUESTS)
                location.update(self.level, self.updater.message)

            # Пропускаем, если шанс говорит не идти
            if not location.travel:
                self.logger.sleep(10, "Пропускаю " + location.console)
                continue

            # Выбираем, куда пойдем
            emoji = location.emoji

            # Отправляем сообщение с локацией
            self.logger.log("Отправляю " + location.console)
            self.updater.update(emoji)

            # Откладываем следующий поход
            self.logger.log("Следующий {} через {:.3f} минут".format(
                location.console,
                location.postpone()
            ))

            # Локация не требует затрат времени, пропускаем задержку
            if location.instant:
                continue

            # Если устали, откладываем отправку всех команд
            if "мало единиц выносливости" in self.updater.message:
                self.logger.log("~Выдохся, поживу без приключений пару часов")

                exhaust = time.time() + COOLDOWN + random.random() * 3600
                self.exhaust = exhaust
                return False

            # Если уже в пути, прерываем отправку команд
            if "сейчас занят другим приключением" in self.updater.message:
                self.logger.log("А, я же не дома")
                return False

            self.logger.sleep(310, "Вернусь через 5 минут")

            # По возвращении деремся с монстром, если он есть
            self.fight(emoji)

            # И ради интереса запрашиваем свой профиль
            if random.random() < 0.4:
                self.hero()

        return True

    def hero(self, quick=False):
        """
        Запрашивает профиль героя и увеличивает уровень
        quick: отправить только запрос с короткой задержкой
        """
        if quick:
            self.updater.update(HERO, 2)
            return True

        if LEVEL_UP in self.updater.message:
            self.logger.log("Ух-ты, новый уровень!")
            self.updater.update(LEVEL_UP)

            if "какую характеристику ты" in self.updater.message:
                self.updater.update(PLUS_ONE)
                self.level += 1
                self.updater.send_group(
                    "Новый уровень: `{}`!".format(self.level))

            else:
                self.logger.log("Странно, где же выбор?")

        return True

    def caravan(self):
        """ Перехватывает КОРОВАН """
        self.updater.update()
        if CARAVAN in self.updater.message:
            self.logger.log("Защищаю караван")
            self.updater.update(CARAVAN)
            self.logger.sleep(45, "~Минутку посплю после каравана", False)

        return True

    def direct_help(self, prefix, command):
        """ Отправляет команду, полученную в формате prefix: command
        prefix: строка до двоеточия в формате prefix level_from (level_to)
        command: строка после, сообщение в формате text x N

        После отправки строительной команды спит 5.5 минут, поэтому убедись,
        что никакие другие процессы не будут перекрыты
        и что последнее сообщение актуально
        """

        text, times = count_help(prefix, command,
                                 self.flag, self.level, self.logger.user)

        if not text:
            return False

        for i in range(times):
            # Команда подходит, отправляем
            self.updater.update(text)

            if "/repair" in text or "/build" in text:
                # Не строим, если не можем
                if "В казне" in self.updater.message:
                    self.updater.send_group("Не из чего строить!")
                    return False

                elif "Битва близко" in self.updater.message:
                    self.updater.send_group("Поздно строить!")
                    return False

                # Спим только если действительно пошли на стройку
                else:
                    self.logger.sleep(310, "Сон от стройки")

            else:
                self.logger.sleep(90, "Сон прямого контроля")

            message_id, _ = self.updater.bot_message
            self.logger.log(SENDING.format(text, i+1, times))
            self.updater.forward_bot_to_group(message_id)

            if times > 1:
                self.logger.sleep(30, "Сон множественной команды", False)

        self.updater.send_group("Всё!")
        return True

    def help_other(self):
        """ Помогает друзьям из Супергруппы """
        message, content = self.updater.group_message

        # Не помогаем сами себе
        if message.from_id == self.client.user_id:
            return False

        parts = content.split(": ")
        # Отделяем команду через двоеточие с пробелом
        if len(parts) == 2:
            return self.direct_help(*parts)

        # Не помогаем, если боев на сегодня слишком много
        if time.time() < self.monster:
            return False

        # Не помогаем на побережье, если не контролируем побережье
        if SHORE in content:
            if self.flag not in content:
                return False

        # Не помогаем в Пустошах, если не из Пустошей
        if not go_wasteland(self.flag, content):
            return False

        command = get_fight_command(content)

        if command:
            self.logger.log("Иду на помощь: {}".format(command))
            self.updater.send_group("+")
            self.updater.update(command)

        if "Слишком много" in self.updater.message:
            self.monster = time.time() + MONSTER_COOLDOWN

        return True

    def fight(self, emoji):
        """ Отправляет команды сражения с монстром """
        # Сначала помогаем друзьям
        self.help_other()

        self.updater.update()
        command = get_fight_command(self.updater.message)

        if command:
            self.logger.sleep(5, "Монстр! Сплю пять секунд перед дракой")
            self.updater.update(command)

            if emoji == SHORE:
                self.updater.send_group(self.flag + SHORE + "! " + command)
            else:
                self.updater.send_group(self.flag + ' ' + command)

        return True

    # Конец
