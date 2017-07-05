# coding=utf-8
"""
Модуль для конкретных и часто используемых обращений к клиенту
"""

import sys

from bot.data import WAR, WAR_COMMANDS, REGROUP, CHATS, WIND
from bot.helpers import get_equipment
from sessions import SUPERGROUP_ID


class Updater(object):
    """ Модуль для конкретных и часто используемых обращений к клиенту """
    def __init__(self, client, logger):
        self.client = client
        self.logger = logger
        self.chats = {}

        self.mid = 0
        self.message = None

    @property
    def bot_message(self):
        """ Последнее сообщение от бота игры """
        return self.client.get_message(self.chats["cw"])

    @property
    def group_message(self):
        """ Последнее сообщение от Супергруппы """
        _, message = self.client.get_message(self.chats["group"], False)
        return message

    @property
    def order(self):
        """ Приказ на основе последнего сообщения в Супергруппе """
        message = self.group_message.lower()
        if message == REGROUP:
            return message
        return WAR.get(WAR_COMMANDS.get(message))

    @property
    def equipment(self):
        """ Возвращает словарь с лучшей экипировкой """
        self.update("/inv")
        return get_equipment(self.message)

    def update_chats(self):
        """ Обновляет список чатов на основе 10 последних диалогов """
        _, entities = self.client.get_dialogs(10)

        for entity in entities:
            name = CHATS.get(entity.id)

            if name:
                self.chats[name] = entity

            elif entity.id == SUPERGROUP_ID:
                self.chats['group'] = entity

        return True

    def send_group(self, message):
        """
        Отправляет сообщение Супергруппе
        message: строка-текст сообщения с Маркдауном
        """
        self.send_message("group", message)

    def send_penguin(self):
        """ Отправляет инвентарь Пингвину """
        self.send_message("trade_bot", "/start")
        self.logger.sleep(3, "Отправляю инвентарь пингвину")

        _, message = self.client.get_message(self.chats["trade_bot"])
        self.send_message("penguin", message)
        return True

    def send_message(self, entity_key, message):
        """ Отправляет сообщение с Маркдауном и без предпросмотра
        entity_key: ключ, под которым записан адресат-entity
        message: текст сообщения """
        self.client.send_message(self.chats[entity_key],
                                 message,
                                 markdown=True,
                                 no_web_page=True)

    def update(self, message=None, sleep=5, wind=None):
        """
        Отправляет сообщение Боту и 7 раз спит, ожидая новый ответ.
        Возвращает True, если был получен новый ответ, и капча пройдена;
        False, если новый ответ не был получен, или он — «ветер»
        message: строка, сообщение к отправке
        sleep: число секунд — пауза после отправки сообщения
        wind: строка-сообщение для вывода в случае ветра, по умолчанию None
        """
        if message:
            self.send_message("cw", message)
            self.logger.sleep(sleep)

        for i in range(1, 7):
            mid, message = self.bot_message

            if self.mid == mid:
                self.logger.sleep(10, "Жду сообщение: {}/6".format(i))

            else:
                self.mid, self.message = mid, message

                # Ветер
                if "завывает" in self.message:
                    if wind is None:
                        wind = "отправку «{}»".format(message)

                    self.logger.log_sexy(WIND, wind + "! :(")
                    return False

                # Пробуем обойти капчу
                return self.captcha()

        # Новый ответ получен не был
        return False

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
        self.send_message("captcha_bot", self.message)
        self.logger.sleep(10, "Десять секунд, жду Капчеватора")

        _, captcha_answer = self.client.get_message(self.chats["captcha_bot"])

        if "Не распознано" in captcha_answer:
            self.stop()

        self.logger.log("Отдаю ответ")
        self.update(captcha_answer)

        return True

    def stop(self):
        """ Останавливает бота """
        self.send_group("У меня тут проблема")
        self.send_group(self.message)
        sys.exit()  # (!) проверить, выключаются ли все боты или один
