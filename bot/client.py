# coding=utf-8
'''
Адаптированный клиент Телетона
'''

import datetime
import os
import random
import sys
import time


from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.tl.functions.messages import ForwardMessagesRequest
from telethon.tl.types import (
    UpdateNewMessage, UpdateNewChannelMessage,
    UpdateShortChatMessage, UpdateShortMessage)
from telethon.utils import get_input_peer

from bot.data import (
    CHATS, TELEGRAM, GAME, TRADE, CAPTCHA, ENOT,
    PLUS_ONE, LEVEL_UP, ATTACK, DEFEND,
    SHORE, WAR, WAR_COMMANDS, HERO,
    COOLDOWN, MONSTER_COOLDOWN, HELLO, VERBS
)
from bot.helpers import (
    count_help, get_equipment, get_fight_command, get_flag, get_level, go_wasteland
)
from bot.locations import create_locations
from bot.logger import Logger
from sessions import API_ID, API_HASH


class FarmBot(TelegramClient):
    ''' Объект бота для каждой сессии '''

    # pylint: disable=too-many-branches
    # pylint: disable=too-many-instance-attributes
    # pylint: disable=too-many-return-statements
    # pylint: disable=too-many-statements
    # todo: remove branches and check

    def __init__(self, user, data, silent=True):
        # Если выводим в лог, очищаем его и начинаем с задержкой
        if silent:
            log_file = 'logs/' + user + '.log'
            with open(log_file, 'w') as target:
                target.truncate()

        else:
            log_file = None

        # Добавляем логгер
        self.logger = Logger(user, log_file, data['girl'])

        # Рассинхронизируем боты
        if log_file:
            self.logger.sleep(600 * random.random(),
                              'Сон рассинхронизации: {}', False)

        # Создаем файл сессии и устанавливаем параметры Телеграма
        super().__init__('sessions/' + user, API_ID, API_HASH, update_workers=4)

        # Массив с entity, которые будут использоваться для запросов через Телетон
        self.chats = {}

        # Телефон аккаунта
        self.phone = data['phone']

        # Номер супергруппы
        self.supergroup = data['supergroup']

        # Название сессии для прямых команд боту
        self.user = user

        # todo: double check all the states
        # Состоятние бота
        # 0 — ничего не делаю
        # 1 — занят
        # 2 — жду ветер
        # 3 — выполняю прямую команду
        # 4 — защищаю
        # 5 — атакую
        # -1 — заблокирован
        self.state = 0

        # Количество раз, которое осталось отправить прямую команду
        self.times = 0

        # Время до следующей передышки
        self.exhaust = time.time()

        # Последняя локация-квест
        self.adventure = None

        # Через сколько вернусь из приключения # todo
        self.back = 0

        # Монстры, с которыми предстоит сразиться
        self.fights = []

        # Последняя локация
        self.location = 0

        # Все локации
        self.locations = create_locations()
        # Перезаписываем шансы локаций, если они указаны
        if 'adventures' in data:
            self.locations[2].command = data['adventures']

        # Время до следующего дня с походами к монстрам
        self.monster = time.time()

        # Последний приказ из Супергруппы
        self.order = None

        # Основной атрибут для увеличения каждый уровень
        self.primary = PLUS_ONE[ATTACK]
        # Перезаписываем характеристику, если она указана
        if LEVEL_UP in data:
            self.primary = PLUS_ONE[data[LEVEL_UP]]

        # Флаг, уровень и обмундирование определим позднее
        self.equipment = {}
        self.flag = None
        self.level = 0

        # Если запускаем в Виндоуз, переименовываем окно
        if os.name == 'nt':
            os.system('title ' + user + ' as FarmBot')

        # Поехали!
        self.logger.log('Сеанс {} открыт'.format(user))

    def connect_with_code(self):
        ''' Подключается к Телеграму и запрашивает код '''
        # Подключаемся к Телеграму
        connected = self.connect()
        if not connected:
            raise ConnectionError

        # Если Телеграм просит код, вводим его и умираем
        # Каждый отдельный аккаунт запускаем через -l
        if not self.is_user_authorized():
            print('Первый запуск. Запрашиваю код...')
            self.send_code_request(self.phone)

            code_ok = False
            while not code_ok:
                code = input('Введите полученный в Телеграме код: ')

                # Двусторонняя верификация
                try:
                    code_ok = self.sign_in(self.phone, code)

                except SessionPasswordNeededError:
                    verified = input(
                        'Введите пароль для двусторонней аутентификации: ')
                    code_ok = self.sign_in(password=verified)

            # Выходим, чтобы запросить код в следующем боте
            sys.exit('Код верный! Перезапускай {}.'.format(self.user))

    def update_handler(self, update):
        ''' Получает обновления от Телетона и обрабатывает их '''
        # todo: sometimes does not read supergroup
        if isinstance(update, UpdateNewMessage):
            self.acknowledge(update.message, update.message.from_id)

        elif isinstance(update, UpdateShortMessage):
            self.acknowledge(update, update.user_id)

        elif isinstance(update, UpdateShortChatMessage):
            self.acknowledge(update, update.from_id)

        elif isinstance(update, UpdateNewChannelMessage):
            if update.message.to_id.channel_id != self.supergroup:
                return

            self.group(update.message)
            self.send_read_acknowledge(self.chats[self.supergroup], update.message)

        else:
            pass

    def set_state(self, state):
        ''' Устанавливает состояние '''
        if state == -1:
            pass

        elif self.state == 5:
            if state != 0 and state != 2:
                return False

        elif self.state == 4:
            if state != 0 and state != 2 and state != 5:
                return False

        elif self.state == 3:
            if state != 0:
                return False

        elif self.state == 2:
            if state != 0:
                return False

        elif self.state == 1:
            if state != 0:
                return False

        elif self.state == 0:
            pass

        elif self.state == -1:
            if state != 0:
                return False

        self.logger.log('Меняю состояние c {} на {}'.format(self.state, state))
        self.state = state
        return True

    def acknowledge(self, message, from_id):
        ''' Отправляет сообщение в нужную функцию '''
        if self.state == -1:
            return

        time.sleep(1.5)

        if from_id == TELEGRAM:
            self.send_read_acknowledge(self.chats[TELEGRAM], message)
            self.telegram(message)

        elif from_id == GAME:
            self.game(message)
            self.send_read_acknowledge(self.chats[GAME], message)

        elif from_id == TRADE:
            self.logger.log('Сообщение от торговца!')
            self.forward(self.chats[TRADE], message.id, self.chats[ENOT])
            self.send_read_acknowledge(self.chats[TRADE], message)

        elif from_id == ENOT:
            self.logger.log('Сообщение от енота!')
            self.send_read_acknowledge(self.chats[ENOT], message)

        # todo: ask for deprecated captcha
        elif from_id == CAPTCHA:
            self.forward(self.chats[CAPTCHA], message.id, self.chats[GAME])
            self.send_read_acknowledge(self.chats[CAPTCHA], message)

    def start(self):
        ''' Главный цикл отправки сообщений '''
        # Подключаемся
        self.connect_with_code()

        # Записываем важные entity
        self.update_chats()

        # Добавляем обработчик входящих событий
        self.add_update_handler(self.update_handler)

        # Определяем изначальные значения
        while not self.equipment or not self.flag or not self.level:
            self.send(self.chats[GAME], '/hero')
            time.sleep(5)
            self.send(self.chats[GAME], '/inv')
            time.sleep(10)

        # Отправляем сообщение о пробуждении
        self.logger.log('Первое пробуждение')
        self.send(self.chats[self.supergroup], HELLO.format(
            self.flag,
            self.user,
            self.level
        ))

        # Начинаем отправлять команды
        while True:
            self.logger.sleep(
                105, '~Сплю минуту в состоянии == ' + str(self.state), False)

            # Бой каждые четыре часа. Час перед утренним боем — 8:00 UTC+0
            now = datetime.datetime.utcnow()

            # С 47-й минуты выходим в бой
            if now.hour % 4 == 0 and now.minute >= 47:
                if self.state == 3:
                    self.send(self.chats[self.supergroup],
                              'Бросаю команду, готовлюсь к бою!')
                    self.times = 0
                    self.set_state(0)
                    time.sleep(5)

                if self.state != 4 and self.state != 5:
                    self.battle(DEFEND)


            # Отправляем отчет, но только один раз
            elif now.hour % 4 == 1 and now.minute <= 12:
                # Первые пять минут обычно ветер
                if now.minute <= 5:
                    continue

                if self.state == 0:
                    continue

                # Если атаковали, надеваем одежду для защиты и добычи
                if self.state == 5:
                    self.equip(DEFEND)

                self.send(self.chats[GAME], '/report')
                time.sleep(2)
                self.send(self.chats[TRADE], '/')
                time.sleep(2)

                # Оповещаем Супергруппу о полученном приказе
                verb = VERBS[self.logger.girl].get(self.state, "Слишком поздно! :(")

                if self.state == 5:
                    self.send(self.chats[self.supergroup], verb + self.order)
                    self.order = None

                elif self.state == 4:
                    self.send(self.chats[self.supergroup], verb + self.flag)

                else:
                    self.send(self.chats[self.supergroup], verb)

                self.set_state(0)

            else:
                if time.time() > self.exhaust and self.state == 0:
                    self.send_locations()

    def telegram(self, message):
        ''' Записывает полученный от Телеграма код '''

        if 'Your login code' in message.message:
            self.logger.log(message.message[:23])

    def game(self, message):
        ''' Отвечает на сообщение бота игры '''
        text = message.message

        # Сообщения с ветром самые приоритетные
        if 'завывает' in text:
            self.set_state(2)
            self.logger.sleep(300, 'Жду ветер 5 минут')
            if self.state == 2:
                self.set_state(0)

        # На приключении
        elif 'сейчас занят другим приключением' in text:
            self.set_state(1)

        # Караваны
        elif '/go' in text:
            self.set_state(1)
            self.send_message(self.chats[GAME], '/go')

        # Слишком много боев
        elif 'Слишком много боев на сегодня' in text:
            self.logger.log('На сегодня хватит боев')
            self.monster = time.time() + MONSTER_COOLDOWN

        # Устал
        elif 'мало единиц выносливости' in text:
            self.logger.log('~Выдохся, поживу без приключений пару часов')
            exhaust = time.time() + COOLDOWN + random.random() * 3600
            self.exhaust = exhaust

        # Оповещаем о потере
        elif 'Твои результаты в бою' in text:
            if 'Вы потеряли' in text:
                self.forward(self.chats[GAME],
                             message.id, self.chats[self.supergroup])

        # Прямые команды
        elif self.state == 3:
            self.logger.log('Результат прямой команды')
            if 'В казне' in text:
                self.set_state(0)
                self.send(self.chats[self.supergroup], 'Не из чего строить!')
                return

            if "Ты пошел" not in message:
                self.forward(self.chats[GAME], message.id, self.chats[self.supergroup])

            if self.times > 0:
                self.logger.log("Осталось: " + str(self.times))
                return

            self.set_state(0)
            self.send(self.chats[self.supergroup], 'Все!')

        # Ответ на /hero
        elif '🏛Твои умения: ' in text:
            self.logger.log('Обновляю профиль')
            self.level = get_level(text)
            self.flag = get_flag(text)

        # Ответ на /inv
        elif 'Содержимое рюкзака' in text:
            self.logger.log('Обновляю инвентарь')
            self.equipment = get_equipment(text)

        # Готовимся к атаке конкретной точки
        elif 'вояка!' in text:
            self.logger.log('Атакую!')
            self.send(self.chats[GAME], self.order)

        # Готовимся к защите конкретной точки
        elif 'защитник!' in text:
            self.logger.log('Защищаю!')
            self.send(self.chats[GAME], self.flag)

        # Готовимся к защите
        elif ' приготовился к ' in text:
            self.logger.log('В бой!')
            if 'защите' in text:
                self.logger.log('Буду защищать!')
                self.set_state(4)

            elif 'атаке' in text:
                self.logger.log('Буду атаковать!')
                self.set_state(5)
                self.equip(ATTACK)

        # Квесты # todo: self.back
        elif 'Ты отправился' in text:
            self.logger.log('Вперед!')
            self.set_state(1)

        # Ответ на квесты
        elif '🔋🔋' in text:
            self.logger.log('Выбираю квест')
            self.locations[self.location].update(self.level, text)

        # Оповещаем о беде
        elif 'питомец в опасности!' in text:
            self.forward(self.chats[self.supergroup],
                         message.id, self.chats[self.supergroup])

        # Просим ручной выбор класса
        elif 'Определись со специализацией' in text:
            self.logger.log('Выберите мне класс!')
            self.send(self.chats[self.supergroup], 'Выберите мне класс!')

        # Запрашиваем повышение уровня
        elif LEVEL_UP in text:
            self.logger.log('Ух-ты, новый уровень!')
            self.send(self.chats[GAME], LEVEL_UP)

        # Выбираем основную характеристику
        elif 'какую характеристику ты' in text:
            self.logger.log('Выбираю характеристику')
            self.send(self.chats[GAME], self.primary)
            self.level += 1
            self.send(self.chats[self.supergroup],
                      'Новый уровень: `{}`!'.format(self.level))

        # Пропускаем ситуацию, когда надеть нечего
        elif 'невозможно выполнить' in text:
            pass

        # Пропускаем надевание предмета
        elif 'Экипирован предмет:' in text:
            pass

        else:
            command = get_fight_command(text)
            if command:
                self.send(self.chats[GAME], command)
                if self.adventure == SHORE:
                    self.send(self.chats[self.supergroup],
                              self.flag + SHORE + "! " + command)
                else:
                    self.send(self.chats[self.supergroup],
                              self.flag + ' ' + command)

            self.set_state(0)

        self.logger.log('Состояние == ' + str(self.state))
        return

    def group(self, message):
        ''' Обрабатывает сообщение группы '''
        while self.state != 0:
            self.logger.sleep(60, 'Пока не могу приступить, посплю немного')

        text = message.message

        # Кто-то другой взял монстра, перезаписываем
        if text.startswith('+'):
            command = '/' + text[2:]
            if command in self.fights:
                self.fights.remove('/' + text[2:])
                return

        parts = message.message.split(': ')

        # Прямая команда должна состоять из двух частей, разделенных двоеточием
        if len(parts) == 2:
            text, times = count_help(parts[0], parts[1],
                                     self.flag, self.level, self.user)

            self.logger.log('Прямая команда: ' + text)
            if text == '/sleep':
                self.logger.log('Сплю, капитан!')
                self.send(self.chats[self.supergroup], 'Сплю, капитан!')
                self.set_state(-1)
                return

            elif text == '/wake':
                if self.state != -1:
                    self.send(self.chats[self.supergroup], 'Я не сплю!')
                    return

                self.set_state(0)
                self.logger.log('Проснулся, капитан!')
                self.send(self.chats[self.supergroup], 'Ну вот, опять работать!')
                return

            delay = 2
            if '/repair' in text or '/build' in text:
                delay = 300

            self.set_state(3)
            self.times = times

            self.logger.sleep(90 * random.random(),
                              'Сон рассинхронизации прямой команды: {}', False)

            if times > 1:
                delay += 10

            for _ in range(times):
                # Команда подходит, отправляем
                if self.state != 3:
                    self.logger.log("Прервали извне")
                    self.times = 0
                    return

                self.times -= 1
                self.send(self.chats[GAME], text)
                self.logger.sleep(delay, 'Сон прямого контроля: {}')

            return

        # Приказ выйти в бой
        order = WAR.get(WAR_COMMANDS.get(text.lower()))
        if order:
            self.logger.log('Приказ на атаку: ' + order)
            self.order = order
            self.battle(ATTACK)
            return

        # Команда сразиться с монстром
        command = get_fight_command(text)
        if not command:
            return

        # Не помогаем на побережье, если не контролируем побережье
        if SHORE in text:
            if self.flag not in text:
                return

        # Не помогаем в Пустошах, если не из Пустошей
        if not go_wasteland(self.flag, text):
            return

        # Не помогаем, если боев на сегодня слишком много
        if time.time() < self.monster or self.state != 0:
            return

        self.fights.append(command)
        # Спим случайное время, чтобы помощник был только один
        time.sleep((30 * random.random()))

        # Идем в бой, если никто другой не успел
        if command in self.fights:
            self.logger.log('Иду на помощь: {}'.format(command))
            self.send(self.chats[GAME], command)
            self.send(self.chats[self.supergroup], '+ `{}`'.format(command[1:]))
        return

    def send_locations(self):
        ''' Отправляется во все локации '''
        for i, location in enumerate(self.locations):
            self.location = i

            if self.state != 0:
                self.logger.log("Отмена задания! Выполняю текущее")
                return

            # Пропускаем, если время идти в локацию еще не пришло
            if time.time() < location.after:
                self.logger.log('{}: следующий поход через {:.3f}'.format(
                    i, (location.after - time.time()) / 60
                ))
                continue

            # Если требует времени, идем как приключение
            if not location.instant:
                self.send(self.chats[GAME], '🗺 Квесты')
                self.logger.sleep(5, 'Сплю после отправки квестов')

            # Пропускаем, если шанс говорит не идти
            if not location.travel:
                self.logger.sleep(10, 'Пропускаю ' + location.console)
                continue

            # Выбираем, куда пойдем
            emoji = location.emoji

            # Отправляем сообщение с локацией
            self.set_state(1)
            sent = self.send(self.chats[GAME], emoji)
            if not sent:
                continue

            # Откладываем следующий поход
            self.logger.log('Следующий {} через {:.3f} минут'.format(
                location.console,
                location.postpone()
            ))

            # Локация не требует затрат времени, пропускаем задержку
            if location.instant:
                self.logger.sleep(5, 'Сплю после мгновенной команды')

            else:
                # todo: delay
                self.adventure = emoji
                self.logger.sleep(300, '~Сплю после долгой команды', False)

                # И ради интереса запрашиваем свой профиль
                if random.random() < 0.4:
                    self.logger.log('Выпал запрос героя')
                    self.send(self.chats[GAME], '/hero')

            self.set_state(0)

        return

    def battle(self, order):
        ''' Переходит в режим атаки или защиты '''
        sent = self.send(self.chats[GAME], HERO)

        if self.state != 0:
            return

        time.sleep(2)

        sent = self.send(self.chats[GAME], order)
        if not sent:
            return

        time.sleep(2)

    def equip(self, state):
        '''
        Надевает указанные предметы
        state: ключ, по которому будут выбраны предметы
        '''
        for _, equip in self.equipment.items():
            if len(equip) == 2:
                item = '/on_{}'.format(equip[state])
                self.logger.log('Надеваю: {}'.format(item))

                sent = self.send(self.chats[GAME], item)
                if not sent:
                    return

                time.sleep(5)

        self.logger.log('Завершаю команду {}'.format(state))
        return

    def send(self, entity, text):
        ''' Сокращение, потому что бот всегда использует Маркдаун '''
        # Не отправляем ничего в оффлайне
        if self.state == -1:
            return False

        # Не отправляем игре в ветер
        if entity == self.chats[GAME] and self.state == 2:
            return False

        self.logger.log('Отправляю: ' + text)
        result = self.send_message(entity, text, parse_mode='markdown')
        if not result:
            raise ConnectionError
        return True

    def forward(self, from_entity, message_id, to_entity):
        ''' Пересылает сообщение от entity к entity '''
        self(
            ForwardMessagesRequest(
                get_input_peer(from_entity),
                [message_id],
                get_input_peer(to_entity)
            )
        )

    def update_chats(self):
        ''' Обновляет список чатов на основе 100 последних диалогов '''
        _, entities = self.get_dialogs(100)

        for entity in entities:
            if entity.id in CHATS:
                self.chats[entity.id] = entity

            elif entity.id == self.supergroup:
                self.chats[self.supergroup] = entity

        return
