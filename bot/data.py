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
    "Сумрачный": "🇰🇮",
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
    "у": "Сумрачный",
    "л": "Лесной форт",
    "г": "Горный форт",
}

GENITIVES = {
    "Красного": "Красный",
    "Синего": "Синий",
    "Черного": "Черный",
    "Белого": "Белый",
    "Желтого": "Желтый",
    "Мятного": "Мятный",
    "Сумрачного": "Сумрачный"
}

DEFEND = "🛡 Защита"
ATTACK = "⚔ Атака"
ALLY = "Союзник"
WIND = "Ветер"

REGROUP = "!!"  # забываем приказ

VERBS = {
    True: {},
    False: {
        ATTACK: "Атаковал", DEFEND: "Защищал",
        ALLY: "Нападали на союзника, поэтому защищал",
        WIND: "Пропустил", None: "Не увидел"
    }
}

for verb, string in VERBS[False].items():
    VERBS[True][verb] = string + "а "
    VERBS[False][verb] = string + " "

RIGHT = "правую руку"
LEFT = "левую руку"
HANDS = {
    DEFEND: "предмет для защиты на ",
    ATTACK: "предмет для атаки на "
}

HELLO = "Просыпается фармитель {} уровня!"

HERO = "🏅Герой"

COOLDOWN = 7200  # Минимальное время между усталостью

CARAVAN = "/go"
FIGHT = "/fight"

LEVEL_UP = "/level_up"
PLUS_ONE = "+1 ⚔Атака"  # Увеличиваем атаку каждый уровень

EQUIP_ITEM = "/on_{}"
