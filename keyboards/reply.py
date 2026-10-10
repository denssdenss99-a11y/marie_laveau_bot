from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_reply_kb(is_admin: bool = False) -> ReplyKeyboardMarkup:
    keyboard = [
        [
            KeyboardButton(text="🎓 Тренажёр"),
            KeyboardButton(text="📝 Сдать экзамен")
        ],
        [
            KeyboardButton(text="📖 База знаний"),
            KeyboardButton(text="📜 Шпаргалка")
        ],
        [
            KeyboardButton(text="👤 Мой профиль")
        ]
    ]

    if is_admin:
        keyboard.append([KeyboardButton(text="⚙️ Панель управления")])

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        is_persistent=True
    )
