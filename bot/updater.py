# coding=utf-8
"""
Модуль для конкретных и часто используемых обращений к клиенту
"""

import sys

from bot.data import WAR, WAR_COMMANDS, REGROUP, CHATS, WIND
from modules.helpers import get_equipment
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
        message, content = self.client.get_message(self.chats["cw"])
        return message.id, content

    @property
    def group_message(self):
        """ Последнее сообщение от Супергруппы """
        return self.client.get_message(self.chats["group"], False)

    @property
    def order(self):
        """ Приказ на основе последнего сообщения в Супергруппе """
        _, content = self.group_message
        content = content.lower()
        if content == REGROUP:
            return content
        return WAR.get(WAR_COMMANDS.get(content))

    @property
    def equipment(self):
        """ Возвращает словарь с лучшей экипировкой """
        self.update("/inv")
        return get_equipment(self.message)

    def update_chats(self):
        """ Обновляет список чатов на основе 100 последних диалогов """
        _, entities = self.client.get_dialogs(100)

        for entity in entities:
            name = CHATS.get(entity.id)

            if name:
                self.chats[name] = entity

            elif entity.id == SUPERGROUP_ID:
                self.chats['group'] = entity

            # self.client.get_message(entity, False)

        return True

    def send_group(self, message, markdown=True):
        """
        Отправляет сообщение Супергруппе
        message: строка-текст сообщения с Маркдауном
        """
        self.send_message("group", message, markdown)

    def send_penguin(self):
        """ Отправляет инвентарь Пингвину (Еноту) """
        self.send_message("trade_bot", "/start")
        self.logger.sleep(3, "Отправляю инвентарь пингвину")

        message, _ = self.client.get_message(self.chats["trade_bot"])
        self.client.forward_message(
            self.chats["trade_bot"],
            message.id,
            self.chats["penguin"]
        )
        return True

    def send_message(self, entity_key, message, markdown=True):
        """ Отправляет сообщение без предпросмотра
        entity_key: ключ, под которым записан адресат-entity
        message: текст сообщения
        markdown: использовать ли Маркдаун
        """
        self.client.send_message(self.chats[entity_key],
                                 message,
                                 markdown=markdown,
                                 no_web_page=True)

    def update(self, text="", sleep=5, wind=None):
        """
        Отправляет сообщение Боту и 7 раз спит, ожидая новый ответ.
        Возвращает True, если был получен новый ответ, и капча пройдена;
        False, если новый ответ не был получен, или он — «ветер»
        text: строка, сообщение к отправке, если пустое, обновляет однажды
        sleep: число секунд — пауза после отправки сообщения
        wind: строка-сообщение для вывода в случае ветра, по умолчанию None
        """
        if not text:
            mid, message = self.bot_message

            if self.mid != mid:
                self.mid, self.message = mid, message

            return True

        self.send_message("cw", text)
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
                        wind = "отправку «{}»".format(text)

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
        sys.exit()

    def forward_bot_to_group(self, message_id):
        """ Пересылает Сообщение из бота игры в супергруппу """
        self.client.forward_message(
            self.chats["cw"],
            message_id,
            self.chats["group"]
        )
