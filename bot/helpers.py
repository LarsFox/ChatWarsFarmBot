# coding=utf-8
"""
Вспомогательные функции
"""

import re

from bot.data import (
    ATTACK, DEFEND, RIGHT, LEFT, EQUIP, WAR, WAR_COMMANDS, GENITIVES, FIGHT)


def go_wasteland(flag, message):
    """ Проверяет, идти ли в битву в Пустоши """
    if any(i in message for i in ("!!", WAR["Мятный"], WAR["Сумрачный"])):
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
        return message[command:command + 27]
    return None


def validate_prefix(prefix, flag, level, user):
    """ Проверяет верность префикса в формате who level_from (level_to)
    who определяет, каким фармителям выполнять команду,
    level_from определяет минимальный уровень для выполнения команды,
    level_to — максимальный
    """
    args = prefix.split()
    # Игнорируем, если не сходится ни имя, ни замок, и команда не для всех
    if args[0] not in (flag, user, '!!'):
        if WAR[WAR_COMMANDS[args[0]]] != flag:
            return False

    count = len(args)
    # Игнорируем, если уровень меньше
    if count == 2 and level < int(args[1]):
        return False

    # Игнорируем, если уровень меньше или больше
    elif count == 3 and (int(args[1]) < level or int(args[2]) > level):
        return False

    return True


def count_command(args, level):
    """ Считает, сколько раз отправить команду в формате text x N
    text будет отправлен боту N раз
    """
    text = args[0]

    # Малышам нечего делать на стройке
    if "/repair" in text or "/build" in text:
        if level < 15:
            return 0

    # Параметр не указан, отправляем один раз
    if len(args) == 1:
        return 1

    # Параметр указан, отправляем нужное количество раз
    elif len(args) == 2:
        return int(args[1])

    return 0


def count_help(prefix, command, flag, level, user):
    """ Проверяет верность полученной команды
    и возвращает текст и количество его отправок.

    Если что-то пойдет не так, вернет None, 0.
    """
    try:
        valid = validate_prefix(prefix, flag, level, user)
        if not valid:
            return None, 0

        # Определяем количество отправок
        args = command.split(" x ")
        return args[0], count_command(args, level)

    except (ValueError, IndexError):
        pass

    # Что-то не так
    return None, 0
