import math
from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.db import get_all_items, get_item, search_items
from keyboards.inline import (
    get_kb_menu_kb,
    get_kb_catalog_page_kb,
    get_kb_item_detail_kb
)
from utils import format_item_detail
from config import ITEMS_PER_PAGE

router = Router()

class SearchState(StatesGroup):
    waiting_for_query = State()

@router.message(F.text == "📖 База знаний")
async def open_kb_menu(message: Message, state: FSMContext):
    await state.clear()
    text = (
        "📖 <b>БАЗА ЗНАНИЙ И СПРАВОЧНИК MARIE LAVEAU</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Здесь ты можешь быстро найти любую позицию меню, освежить в памяти состав, "
        "аллергены или подачу перед выходом к гостю.\n\n"
        "💡 <i>Лайфхак для зала:</i> ты можешь искать прямо из любого чата! "
        "Набери в поле ввода имя бота и название блюда: <code>@имя_бота тартар</code>"
    )
    await message.answer(text, reply_markup=get_kb_menu_kb(), parse_mode="HTML")

@router.callback_query(F.data == "kb:home")
async def cb_kb_home(call: CallbackQuery, state: FSMContext):
    await state.clear()
    text = (
        "📖 <b>БАЗА ЗНАНИЙ MARIE LAVEAU</b>\n"
        "Выбери раздел каталога или воспользуйся поиском:"
    )
    await call.message.edit_text(text, reply_markup=get_kb_menu_kb(), parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data.startswith("kb:cat:"))
async def cb_catalog_page(call: CallbackQuery):
    parts = call.data.split(":")
    cat = parts[2]
    page = int(parts[3])

    items = await get_all_items(category=cat)
    total_items = len(items)
    total_pages = max(1, math.ceil(total_items / ITEMS_PER_PAGE))
    page = max(0, min(page, total_pages - 1))

    start = page * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    page_items = items[start:end]

    cat_title = "🍸 КОКТЕЙЛИ" if cat == "cocktails" else "🍲 КУХНЯ"
    text = (
        f"<b>{cat_title} | Справочник</b>\n"
        f"Всего позиций в разделе: <b>{total_items}</b>\n"
        f"Страница <b>{page+1} из {total_pages}</b>\n\n"
        f"<i>Нажми на любую позицию, чтобы открыть полную карточку:</i>"
    )

    kb = get_kb_catalog_page_kb(page_items, page, total_pages, cat)
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data.startswith("kb:item:"))
async def cb_item_detail(call: CallbackQuery):
    parts = call.data.split(":")
    item_id = parts[2]
    cat = parts[3]
    page = int(parts[4])

    item = await get_item(item_id)
    if not item:
        await call.answer("Позиция не найдена", show_alert=True)
        return

    text = format_item_detail(item)
    kb = get_kb_item_detail_kb(cat, page)
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data == "kb:search")
async def cb_kb_search_prompt(call: CallbackQuery, state: FSMContext):
    await state.set_state(SearchState.waiting_for_query)
    text = (
        "🔍 <b>ПОИСК ПО МЕНЮ</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Отправь текстовым сообщением то, что ищешь:\n"
        "• Название блюда или коктейля (например: <i>митан, тартар, щека</i>)\n"
        "• Ингредиент или соус (например: <i>бурбон, блю чиз, манго</i>)\n"
        "• Аллерген (например: <i>лактоза, орехи</i>)"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="↩️ Отмена", callback_data="kb:home")]
    ])
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()

@router.message(SearchState.waiting_for_query)
async def process_search_query(message: Message, state: FSMContext):
    query = message.text.strip()
    await state.clear()

    results = await search_items(query)
    if not results:
        text = f"По запросу «<b>{query}</b>» ничего не найдено 🤷\nПопробуй сформулировать иначе."
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Попробовать снова", callback_data="kb:search")],
            [InlineKeyboardButton(text="📖 В меню базы", callback_data="kb:home")]
        ])
        await message.answer(text, reply_markup=kb, parse_mode="HTML")
        return

    text = f"🔍 <b>Результаты поиска по запросу «{query}»</b> ({len(results)} найдено):\nНажми для просмотра:"
    buttons = []
    for it in results[:10]:
        icon = "🍸" if it['category'] == 'cocktails' else "🍲"
        buttons.append([InlineKeyboardButton(
            text=f"{icon} {it['name']} ({it.get('price', '')})",
            callback_data=f"kb:item:{it['id']}:{it['category']}:0"
        )])

    buttons.append([InlineKeyboardButton(text="🔍 Новый поиск", callback_data="kb:search")])
    buttons.append([InlineKeyboardButton(text="📖 В меню базы", callback_data="kb:home")])

    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")

# Telegram Inline Query mode (@bot query)
@router.inline_query()
async def inline_search(inline_query: InlineQuery):
    query = inline_query.query.strip()
    if not query:
        items = await get_all_items()
        sample = items[:15]
    else:
        sample = await search_items(query)

    articles = []
    for it in sample[:25]:
        content = format_item_detail(it)
        desc = it.get('composition', '')[:100]
        icon = "🍸" if it['category'] == 'cocktails' else "🍲"

        articles.append(InlineQueryResultArticle(
            id=it['id'],
            title=f"{icon} {it['name']} ({it.get('price', '')})",
            description=desc,
            input_message_content=InputTextMessageContent(
                message_text=content,
                parse_mode="HTML"
            )
        ))

    await inline_query.answer(articles, cache_time=10)
