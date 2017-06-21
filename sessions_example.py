# coding=utf-8

# Создаем файл sessions на основе этого файла
# Подставляем свои параметры для каждого акканута

# Берем из Телеграма
API_ID = 123456
API_HASH = "0123456789abcdef0123456789abcdef"

# Супергруппа, в которую будем писать о боях
SUPERGROUP_ID = 1123894847

ENTER_CAVE = 30  # Уровень, с которого начинаем ходить в пещеру 

SESSIONS = {
    "1": {                        # имя, под которым запускаем сессию
        "phone": "+12345678901",
        "flag": "Белый",          # все цвета смотрим в словаре WAR
        "level": 0,               # отправляет профиль Пингвину на 15+ 
        "girl": True,             # влияет на род глаголов в 3-м лице :)
        "equip": {                # указываем лучший предмет
            "right": {            # номера берем по команде /inv у бота
                "defend": 119,    # если не меняем, указываем только один
            },
            "left": {
                "attack": 113,    # режим атаки
                "defend": 212,    # режим сбора и защиты
            }
        },
    }
}
