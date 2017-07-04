# coding=utf-8
"""
Модуль для конкретных и часто используемых обращений к клиенту
"""

from bot.data import WAR, WAR_COMMANDS, REGROUP, CHATS
from sessions import SUPERGROUP_ID


class Updater(object):
    """ Модуль для конкретных и часто используемых обращений к клиенту """
    def __init__(self, client, logger):
        self.client = client
        self.logger = logger
        self.chats = {}

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
