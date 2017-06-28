# coding=utf-8
"""
Модуль для конкретных и часто используемых обращений к клиенту
"""

from bot.data import WAR, WAR_COMMANDS, REGROUP


class Updater(object):
    """ Модуль для конкретных и часто используемых обращений к клиенту """
    def __init__(self, client, logger, chats):
        self.client = client
        self.logger = logger
        self.chats = chats

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

    def send_group(self, message):
        """ Отправляет сообщение Супергруппе """
        self.client.send_text(self.chats["group"], message)

    def send_penguin(self):
        """ Отправляет инвентарь Пингвину """
        self.client.send_text(self.chats["trade_bot"], "/start")
        self.logger.sleep(3, "Отправляю инвентарь пингвину")

        _, message = self.client.get_message(self.chats["trade_bot"])
        self.client.send_text(self.chats["penguin"], message)
        return True
