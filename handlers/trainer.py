from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from database.db import get_next_training_item, get_item, record_answer
from keyboards.inline import (
    get_category_selector_kb,
    get_flashcard_question_kb,
    get_flashcard_answer_kb
)
from utils import format_card_question, format_card_answer

router = Router()

@router.message(F.text == "🎓 Тренажёр")
async def start_trainer_select(message: Message):
    text = (
        "🎓 <b>РЕЖИМ ТРЕНАЖЁРА (ФЛЕШ-КАРТОЧКИ)</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Выбери раздел для тренировки.\n\n"
        "<i>Как это работает:</i>\n"
        "1. Бот присылает название позиции.\n"
        "2. Ты вспоминаешь состав, подачу, вкус или аллергены.\n"
        "3. Нажимаешь <b>«Показать ответ»</b> и сверяешься.\n"
        "4. Оцениваешь себя — бот автоматически чаще повторяет то, в чём ты ошибся!"
    )
    await message.answer(
        text,
        reply_markup=get_category_selector_kb(action_prefix="train"),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("train:cat:"))
async def cb_start_training_cat(call: CallbackQuery):
    cat = call.data.split(":")[2]
    user_id = call.from_user.id

    item = await get_next_training_item(user_id, cat)
    if not item:
        if cat == 'mistakes':
            await call.answer("🎉 Отлично! У тебя пока нет позиций с ошибками для повторения.", show_alert=True)
        else:
            await call.answer("Позиции не найдены.", show_alert=True)
        return

    text = format_card_question(item, is_exam=False)
    kb = get_flashcard_question_kb(item['id'], cat, is_exam=False)
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data.startswith("train:reveal:"))
async def cb_reveal_answer(call: CallbackQuery):
    parts = call.data.split(":")
    item_id = parts[2]
    cat = parts[3]

    item = await get_item(item_id)
    if not item:
        await call.answer("Ошибка: позиция не найдена", show_alert=True)
        return

    text = format_card_answer(item, is_exam=False)
    kb = get_flashcard_answer_kb(item['id'], cat, is_exam=False)
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data.startswith("train:grade:"))
async def cb_grade_answer(call: CallbackQuery):
    parts = call.data.split(":")
    item_id = parts[2]
    cat = parts[3]
    grade = parts[4]
    user_id = call.from_user.id

    await record_answer(user_id, item_id, grade)

    grade_feedback = {
        'known': "🟢 Отлично! Усвоено.",
        'partial': "🟡 Хорошо, закрепляем.",
        'unknown': "🔴 Запомнили. Повторим эту позицию скоро!"
    }
    await call.answer(grade_feedback.get(grade, "Сохранено!"))

    # Automatically load next card
    next_item = await get_next_training_item(user_id, cat)
    if not next_item:
        if cat == 'mistakes':
            await call.message.edit_text(
                "🎉 <b>Великолепно!</b> Ты повторил все проблемные карточки!\n"
                "Можно вернуться к полному меню или сдать экзамен.",
                reply_markup=get_category_selector_kb("train"),
                parse_mode="HTML"
            )
            return
        next_item = await get_next_training_item(user_id, 'all')

    text = format_card_question(next_item, is_exam=False)
    kb = get_flashcard_question_kb(next_item['id'], cat, is_exam=False)
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data.startswith("train:next:"))
async def cb_next_card(call: CallbackQuery):
    cat = call.data.split(":")[2]
    user_id = call.from_user.id

    next_item = await get_next_training_item(user_id, cat)
    if not next_item:
        await call.answer("Карточки закончились.", show_alert=True)
        return

    text = format_card_question(next_item, is_exam=False)
    kb = get_flashcard_question_kb(next_item['id'], cat, is_exam=False)
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data == "train:stop")
async def cb_stop_trainer(call: CallbackQuery):
    await call.message.edit_text(
        "🏁 <b>Тренировка завершена!</b>\n"
        "Твой прогресс сохранён в профиле. Отличная работа!",
        parse_mode="HTML"
    )
    await call.answer()
