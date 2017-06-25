# coding=utf-8
"""
Игровые данные
"""

# Обязательно проверяем, что в топ-10 есть все эти диалоги
CHATS = {
    777000: "telegram",         # Telegram
    265204902: "cw",            # Бот игры
    278525885: "trade_bot",     # Бот торговли
    313998026: "captcha_bot",   # Бот капчи
    389922706: "penguin",       # Бот Пингвин для склада
}

WAR = {
    "Красный": "🇮🇲",
    "Черный": "🇬🇵",
    "Белый": "🇨🇾",
    "Желтый": "🇻🇦",
    "Синий": "🇪🇺",
    "Мятный": "🇲🇴",
    "Сумеречный": "🇰🇮",
    "Лесной форт": "🌲Лесной форт",
    "Горный форт": "⛰Горный форт"
}

WAR_COMMANDS = {
    "к": "Красный",
    "ч": "Черный",
    "б": "Белый",
    "ж": "Желтый",
    "с": "Синий",
    "м": "Мятный",
    "у": "Сумеречный",
    "л": "Лесной форт",
    "г": "Горный форт",
}

DEFEND = "🛡 Защита"
ATTACK = "⚔ Атака"

REGROUP = "!!"  # забываем приказ
STATUSES = {None: "Отдых", ATTACK: "Атака на", DEFEND: "Защита "}
VERBS = {False: {ATTACK: "Атаковал", DEFEND: "Защищал", None: "Не заметил"}, True: {}}

for verb, string in VERBS[False].items():
    VERBS[True][verb] = string + "а "
    VERBS[False][verb] = string + " "

HERO = "🏅Герой"

COOLDOWN = 7200  # Минимальное время между усталостью

CARAVAN = "/go"
FIGHT = "/fight"

LEVEL_UP = "/level_up"
PLUS_ONE = "+1 ⚔Атака"  # Увеличиваем атаку каждый уровень

EQUIP_ITEM = "/on_{}"
