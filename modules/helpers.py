# coding=utf-8
"""
Вспомогательные функции
"""

import re


from bot.data import ATTACK, DEFEND, RIGHT, LEFT, EQUIP, \
                     WAR, GENITIVES, FIGHT


def go_wasteland(flag, message):
    """ Проверяет идти ли в битву в Пустоши """
    if WAR["Мятный"] in message or WAR["Сумрачный"] in message:
        return flag in message
    return True


def get_equipment(message):
    """ Возвращает словарь с лучшими предметами """
    equip = {LEFT: {ATTACK: 0, DEFEND: 0}, RIGHT: {ATTACK: 0, DEFEND: 0}}

    # Проверяем каждый предмет
    for item in re.findall("(?<=_)[0-9]+", message):
        for slot, slot_items in EQUIP.items():
            stats = slot_items.get(int(item))

            # Пропускаем, если предмет в ячейке не используется
            if not stats:
                continue

            # Проверяем атрибуты предмета
            for stat_name, value in stats.items():
                current = slot_items.get(equip[slot][stat_name])

                # Если находим лучший предмет, записываем его
                if not current or current.get(stat_name, 0) < value:
                    equip[slot][stat_name] = int(item)

    # Если предмет лучший во всех случаях, убираем его лишние упоминания
    for slot, slot_items in equip.items():
        equip[slot] = remove_duplicate_values(slot_items)
    return equip


def remove_duplicate_values(dictionary):
    """ Удаляет ключи, значения которых повторяются """
    result = {}
    for key, value in dictionary.items():
        if value not in result.values():
            result[key] = value
    return result


def get_level(message):
    """ Извлекает уровень из профиля героя /hero """
    found = re.findall("Уровень: (.*?)\n", message)
    return int(found[0])


def get_flag(message):
    """ Извлекает флаг замка из профиля /hero """
    found = re.findall(".* замка", message)[0].split()
    return WAR[GENITIVES.get(found[-2])]


def get_fight_command(message):
    """ Извлекает команду боя в формате /fight_abcdef0123456789abc """
    if FIGHT in message:
        command = message.index(FIGHT)
        return message[command:command+27]

    return None
