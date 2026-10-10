from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import ITEMS_PER_PAGE

def get_category_selector_kb(action_prefix: str = "train") -> InlineKeyboardMarkup:
    """
    Selection keyboard for trainer or exam
    """
    buttons = [
        [InlineKeyboardButton(text="🍸 Коктейли (31)", callback_data=f"{action_prefix}:cat:cocktails")],
        [InlineKeyboardButton(text="🍲 Кухня (43)", callback_data=f"{action_prefix}:cat:food")],
        [InlineKeyboardButton(text="🎲 Всё меню (74)", callback_data=f"{action_prefix}:cat:all")]
    ]
    if action_prefix == "train":
        buttons.append([InlineKeyboardButton(text="⚠️ Работа над ошибками", callback_data=f"{action_prefix}:cat:mistakes")])
    
    buttons.append([InlineKeyboardButton(text="↩️ В главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_flashcard_question_kb(item_id: str, category: str, is_exam: bool = False) -> InlineKeyboardMarkup:
    prefix = "exam" if is_exam else "train"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👁 Показать ответ", callback_data=f"{prefix}:reveal:{item_id}:{category}")],
        [InlineKeyboardButton(text="🛑 Завершить", callback_data=f"{prefix}:stop")]
    ])

def get_flashcard_answer_kb(item_id: str, category: str, is_exam: bool = False) -> InlineKeyboardMarkup:
    if is_exam:
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🟢 Вспомнил верно (+1)", callback_data=f"exam:grade:{item_id}:1"),
                InlineKeyboardButton(text="🔴 Ошибся (0)", callback_data=f"exam:grade:{item_id}:0")
            ],
            [InlineKeyboardButton(text="🛑 Завершить досрочно", callback_data="exam:stop")]
        ])
    else:
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🟢 Знал всё", callback_data=f"train:grade:{item_id}:{category}:known"),
                InlineKeyboardButton(text="🟡 Частично", callback_data=f"train:grade:{item_id}:{category}:partial"),
                InlineKeyboardButton(text="🔴 Не знал", callback_data=f"train:grade:{item_id}:{category}:unknown")
            ],
            [
                InlineKeyboardButton(text="➡️ Следующая карточка", callback_data=f"train:next:{category}"),
                InlineKeyboardButton(text="🛑 Закончить", callback_data="train:stop")
            ]
        ])

def get_kb_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🍸 Каталог Коктейлей", callback_data="kb:cat:cocktails:0"),
            InlineKeyboardButton(text="🍲 Каталог Кухни", callback_data="kb:cat:food:0")
        ],
        [InlineKeyboardButton(text="🔍 Поиск по названию / ингредиенту", callback_data="kb:search")],
        [InlineKeyboardButton(text="↩️ В главное меню", callback_data="main_menu")]
    ])

def get_kb_catalog_page_kb(items: list, page: int, total_pages: int, category: str) -> InlineKeyboardMarkup:
    buttons = []
    # Items buttons
    for it in items:
        icon = "🍸" if it['category'] == 'cocktails' else "🍲"
        buttons.append([InlineKeyboardButton(text=f"{icon} {it['name']}", callback_data=f"kb:item:{it['id']}:{category}:{page}")])

    # Pagination row
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"kb:cat:{category}:{page-1}"))
    
    nav_row.append(InlineKeyboardButton(text=f"Стр. {page+1}/{total_pages}", callback_data="noop"))
    
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"kb:cat:{category}:{page+1}"))

    buttons.append(nav_row)
    buttons.append([InlineKeyboardButton(text="↩️ К разделам базы", callback_data="kb:home")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_kb_item_detail_kb(category: str, page: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад к списку", callback_data=f"kb:cat:{category}:{page}")],
        [InlineKeyboardButton(text="📖 К разделам базы", callback_data="kb:home")]
    ])

def get_guides_menu_kb(guides: list) -> InlineKeyboardMarkup:
    buttons = []
    for g in guides:
        buttons.append([InlineKeyboardButton(text=g['title'], callback_data=f"guide:{g['id']}")])
    buttons.append([InlineKeyboardButton(text="↩️ В главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_guide_detail_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад к шпаргалкам", callback_data="guides:home")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])

def get_admin_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎯 Назначить экзамен стажёру", callback_data="admin:assign:start")],
        [InlineKeyboardButton(text="👥 Список сотрудников и прогресс", callback_data="admin:users")],
        [InlineKeyboardButton(text="👑 Управление админами (Роли)", callback_data="admin:roles:list")],
        [InlineKeyboardButton(text="📊 Аналитика ошибок (Топ)", callback_data="admin:analytics")],
        [InlineKeyboardButton(text="🏆 Протокол экзаменов", callback_data="admin:exams")],
        [InlineKeyboardButton(text="🔄 Перезагрузить меню из JSON", callback_data="admin:reload")],
        [InlineKeyboardButton(text="↩️ В главное меню", callback_data="main_menu")]
    ])
