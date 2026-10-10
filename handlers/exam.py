from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database.db import (
    save_exam_result,
    record_answer,
    get_user,
    get_pending_assigned_exam
)
from quiz_engine import generate_self_exam
from keyboards.inline import get_category_selector_kb
from config import ADMIN_IDS

router = Router()

# In-memory storage for active self-exams
# user_id -> {'category': str, 'questions': list, 'index': int, 'score': int, 'selected': set(), 'total': int}
self_exams = {}

@router.message(F.text == "📝 Сдать экзамен")
async def start_exam_menu(message: Message):
    user_id = message.from_user.id
    pending = await get_pending_assigned_exam(user_id)

    if pending:
        cat_names = {'cocktails': 'Коктейли', 'food': 'Кухня', 'all': 'Всё меню'}
        cat_title = cat_names.get(pending['category'], pending['category'])
        text = (
            f"🚨 <b>ВАМ НАЗНАЧЕН ОФИЦИАЛЬНЫЙ ЭКЗАМЕН!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Менеджер бара назначил вам голосовую аттестацию:\n"
            f"• Раздел: <b>{cat_title}</b>\n"
            f"• Количество билетов: <b>{pending['ticket_count']}</b>\n"
            f"• Формат: <b>Голосовые ответы (состав, подача, презентация)</b>\n\n"
            f"Нажмите кнопку ниже, чтобы приступить к сдаче билетов:"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎙 Начать назначенный экзамен", callback_data=f"voice_exam:start:{pending['id']}")],
            [InlineKeyboardButton(text="🎮 Или пройти самостоятельный тест", callback_data="exam:self_menu")]
        ])
        await message.answer(text, reply_markup=kb, parse_mode="HTML")
        return

    await show_self_exam_categories(message)

async def show_self_exam_categories(target):
    text = (
        "🎮 <b>САМОСТОЯТЕЛЬНАЯ АТТЕСТАЦИЯ (ИНТЕРАКТИВ)</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Никаких длинных текстов и скучных тестов!\n\n"
        "<i>Формат вопросов:</i>\n"
        "• 🧩 <b>Конструктор «Собери состав»:</b> нажимай только на те ингредиенты, которые входят в позицию.\n"
        "• 🕵️ <b>«Найди лишнее»:</b> вычисли подмешанный фальшивый ингредиент-шпион.\n\n"
        "Выбери раздел для проверки:"
    )
    kb = get_category_selector_kb(action_prefix="exam")
    if isinstance(target, Message):
        await target.answer(text, reply_markup=kb, parse_mode="HTML")
    else:
        await target.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data == "exam:self_menu")
async def cb_self_menu(call: CallbackQuery):
    await show_self_exam_categories(call)
    await call.answer()

@router.callback_query(F.data.startswith("exam:cat:"))
async def cb_start_self_exam(call: CallbackQuery):
    cat = call.data.split(":")[2]
    user_id = call.from_user.id

    questions = await generate_self_exam(category=cat, count=10)
    if not questions:
        await call.answer("Не удалось сгенерировать вопросы", show_alert=True)
        return

    self_exams[user_id] = {
        'category': cat,
        'questions': questions,
        'index': 0,
        'score': 0,
        'selected': set(),
        'total': len(questions),
        'mistakes': []
    }

    await render_quiz_question(call.message, user_id)
    await call.answer()

async def render_quiz_question(message: Message, user_id: int):
    session = self_exams.get(user_id)
    if not session:
        return

    q = session['questions'][session['index']]
    cur_num = session['index'] + 1
    total = session['total']
    icon = "🍸" if q['category'] == 'cocktails' else "🍲"

    if q['type'] == 'builder':
        selected = session['selected']
        text = (
            f"🧩 <b>ВОПРОС {cur_num}/{total} | Собери состав</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Позиция: {icon} <b>{q['item_name']}</b>\n"
            f"<i>Отметь ровно {q['target_count']} ингредиента, которые входят в состав:</i>"
        )
        buttons = []
        for idx, opt in enumerate(q['options']):
            check = "✅" if idx in selected else "▫️"
            btn_text = f"{check} {opt['text']}"
            buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"quiz:toggle:{idx}")])

        buttons.append([
            InlineKeyboardButton(text="🎯 Проверить ответ", callback_data="quiz:check_builder"),
            InlineKeyboardButton(text="🛑 Выйти", callback_data="quiz:stop")
        ])
    else:
        # Imposter question
        text = (
            f"🕵️ <b>ВОПРОС {cur_num}/{total} | Найди лишнее</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Позиция: {icon} <b>{q['item_name']}</b>\n"
            f"<i>Какой из этих ингредиентов ЗДЕСЬ ЛИШНИЙ и не входит в состав?</i>"
        )
        buttons = []
        for idx, opt in enumerate(q['options']):
            buttons.append([InlineKeyboardButton(text=f"❌ {opt['text']}", callback_data=f"quiz:imposter:{idx}")])
        buttons.append([InlineKeyboardButton(text="🛑 Выйти", callback_data="quiz:stop")])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    try:
        await message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        await message.answer(text, reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data.startswith("quiz:toggle:"))
async def cb_quiz_toggle(call: CallbackQuery):
    user_id = call.from_user.id
    session = self_exams.get(user_id)
    if not session:
        await call.answer("Сессия истекла", show_alert=True)
        return

    opt_idx = int(call.data.split(":")[2])
    if opt_idx in session['selected']:
        session['selected'].remove(opt_idx)
    else:
        session['selected'].add(opt_idx)

    await render_quiz_question(call.message, user_id)
    await call.answer()

@router.callback_query(F.data == "quiz:check_builder")
async def cb_check_builder(call: CallbackQuery):
    user_id = call.from_user.id
    session = self_exams.get(user_id)
    if not session:
        await call.answer("Сессия истекла", show_alert=True)
        return

    q = session['questions'][session['index']]
    selected_indices = session['selected']

    # Evaluate
    correct_indices = {i for i, opt in enumerate(q['options']) if opt['correct']}

    if selected_indices == correct_indices:
        session['score'] += 1
        await call.answer("🟢 ВЕРНО! Идеально собрано!", show_alert=False)
        await record_answer(user_id, q['item_id'], 'known')
    else:
        await record_answer(user_id, q['item_id'], 'unknown')
        session['mistakes'].append({
            'name': q['item_name'],
            'comp': q['full_composition']
        })
        await call.answer("🔴 Ошибка в рецептуре!", show_alert=False)

    # Next question
    session['index'] += 1
    session['selected'] = set()

    if session['index'] < session['total']:
        await render_quiz_question(call.message, user_id)
    else:
        await finish_self_exam(call.message, user_id)

@router.callback_query(F.data.startswith("quiz:imposter:"))
async def cb_check_imposter(call: CallbackQuery):
    user_id = call.from_user.id
    session = self_exams.get(user_id)
    if not session:
        await call.answer("Сессия истекла", show_alert=True)
        return

    q = session['questions'][session['index']]
    opt_idx = int(call.data.split(":")[2])
    chosen_opt = q['options'][opt_idx]

    if chosen_opt.get('is_imposter', False) or (chosen_opt.get('correct') is False):
        session['score'] += 1
        await call.answer("🟢 ТОЧНО! Вычислен лишний ингредиент!", show_alert=False)
        await record_answer(user_id, q['item_id'], 'known')
    else:
        await record_answer(user_id, q['item_id'], 'unknown')
        session['mistakes'].append({
            'name': q['item_name'],
            'comp': q['full_composition'],
            'imposter': q['imposter']
        })
        await call.answer(f"🔴 Мимо! Лишним был: {q['imposter']}", show_alert=False)

    session['index'] += 1
    session['selected'] = set()

    if session['index'] < session['total']:
        await render_quiz_question(call.message, user_id)
    else:
        await finish_self_exam(call.message, user_id)

async def finish_self_exam(message: Message, user_id: int):
    session = self_exams.get(user_id)
    if not session:
        return

    score = session['score']
    total = session['total']
    cat = session['category']
    mistakes = session['mistakes']
    del self_exams[user_id]

    pct = await save_exam_result(user_id, cat, score, total)
    user = await get_user(user_id)

    if pct >= 85:
        verdict = "🟢 <b>ОТЛИЧНЫЙ РЕЗУЛЬТАТ!</b> Ты прекрасно ориентируешься в составе меню!"
    elif pct >= 70:
        verdict = "🟡 <b>ХОРОШО, НО ЕСТЬ ОШИБКИ.</b> Рекомендуем пройти «Работу над ошибками»."
    else:
        verdict = "🔴 <b>НЕУДОВЛЕТВОРИТЕЛЬНО.</b> Нужно подучить состав в тренажёре."

    text = (
        f"🏁 <b>АТТЕСТАЦИЯ ЗАВЕРШЕНА!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Правильных ответов: <b>{score} из {total}</b> ({pct}%)\n"
        f"{verdict}\n\n"
    )

    if mistakes:
        text += "⚠️ <b>Разбор твоих ошибок:</b>\n"
        for m in mistakes[:4]:
            text += f"• <b>{m['name']}</b>: <i>{m['comp']}</i>\n"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Пройти ещё раз", callback_data=f"exam:cat:{cat}")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])

    await message.edit_text(text, reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data == "quiz:stop")
async def cb_quiz_stop(call: CallbackQuery):
    user_id = call.from_user.id
    if user_id in self_exams:
        del self_exams[user_id]
    await call.message.edit_text("🛑 Аттестация прервана. Результаты не сохранены.", parse_mode="HTML")
    await call.answer()
