# coding=utf-8
"""
Образец файла sessions, на основе которого будут созданы остальные боты.

Для работы создаем свой файл sessions.py на основе этого файла,
подставляя в него значения для каждого аккаунта.

Название сессии не чувствительно к регистру.
С 15-го уровня становится доступен ChatWarsTradeBot.
Уровень, с которого стоит ходить в пещеру, устанавливаем сами.

Перед запуском убедитесь, что бот надел лучшую одежду для защиты и сбора.

Бот требует наличия в десяти первых диалогах:
    * Бота игры @ChatWarsBot
    * Бота торговли @ChatWarsTradeBot
    * Бота Пингвина для твинков @PenguindrumStockBot
    * Бота Капчеватора для капчи @ChatWarsCaptchaBot

А также общего канала, в которую он будет отписываться
о боях и командах. В эту же группу перед боем отправляем приказ.
Соответствие замков и кодовых слов смотрим в файле data.py

Параметры для вызова main.py:
    -s: выбираем куда логгировать: в файл или в консоль
    -l: проверяем логин и вводим телефон (только для одного пользователя).
        Используем для первого ввода кода и создания файла .session
    -c: показываем код в запущенном ТГ (только для одного пользователя).
        Помогает при восстановлении доступа с запущенной сессией
    -r: «перезапуск»: все действия откладываются, чтобы не спамить
        при массовых перезагрузках

Команды-приказы — куда бот пойдет в атаку.
Не чувствительны к регистру.
Если совпадает с цветом замка или союзника, бот остается в защите.
    к: Красный,
    ч: Черный,
    б: Белый,
    ж: Желтый,
    с: Синий,
    м: Мятный,
    у: Сумеречный,
    л: Лесной форт,
    г: Горный форт,

Сейчас бот умеет:
    * Ходить в пещеру и лес
    * Ходить в бой
    * Отправлять свой инвентарь Пингвину после каждого боя
    * Надевать свои лучшие предметы перед атакой и защитой
    * Помогать с монстрами /fight
    * Защищать КОРОВАНЫ /go
"""

# Берем из Телеграма
API_ID = 123456
API_HASH = "0123456789abcdef0123456789abcdef"

# ТГ номер супергруппы, в которую будем писать о боях
SUPERGROUP_ID = 1123894847

CAVE_LEVEL = 30    # Уровень, с которого начинаем ходить в пещеру
CAVE_CHANCE = 0.5  # Среднее количество походов в пещеру

SESSIONS = {
    "S1": {                       # запуск: python main.py s1, лог: s1.log
        "phone": "+12345678901",
        "girl": True,             # влияет на род глаголов в 3-м лице :)
        "equip": {                # указываем номер лучшего предмета
            RIGHT: {            # правая рука: меч, копье, кирка или молот
                DEFEND: 119,      # если не меняем, указываем только один
            },
            LEFT: {             # левая рука: щит или кинжал
                ATTACK: 113,      # надевает перед атакой, если есть приказ
                DEFEND: 212,      # надевает после атаки
            }
        },
    },
    "Session-2": {                # продолжаем для второго аккаунта
    }                             # запуск обоих: python main.py s1 session-2
}
