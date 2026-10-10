import json
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.db import (
    get_assigned_exam,
    get_item,
    update_assigned_exam_status,
    save_voice_submission,
    get_voice_submissions,
    grade_voice_submission,
    check_exam_grading_completed,
    get_user
)
from utils import format_card_answer

router = Router()

class VoiceExamState(StatesGroup):
    recording = State()

# In-memory storage for active voice recordings
# user_id -> {'exam_id': int, 'item_ids': list, 'index': int, 'total': int}
active_recordings = {}

@router.callback_query(F.data.startswith("voice_exam:start:"))
async def cb_start_voice_exam(call: CallbackQuery, state: FSMContext):
    exam_id = int(call.data.split(":")[2])
    exam = await get_assigned_exam(exam_id)

    if not exam:
        await call.answer("Экзамен не найден", show_alert=True)
        return

    item_ids = json.loads(exam['items_json'])
    user_id = call.from_user.id

    active_recordings[user_id] = {
        'exam_id': exam_id,
        'item_ids': item_ids,
        'index': 0,
        'total': len(item_ids)
    }

    await update_assigned_exam_status(exam_id, 'in_progress')
    await state.set_state(VoiceExamState.recording)

    await send_ticket_prompt(call.message, user_id)
    await call.answer()

async def send_ticket_prompt(message: Message, user_id: int):
    session = active_recordings.get(user_id)
    if not session:
        return

    cur_idx = session['index']
    total = session['total']
    item_id = session['item_ids'][cur_idx]
    item = await get_item(item_id)

    icon = "🍸" if item['category'] == 'cocktails' else "🍲"

    text = (
        f"🎙 <b>БИЛЕТ {cur_idx + 1} из {total} | {icon} {item['category'].upper()}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Позиция: <b>{item['name']}</b> ({item.get('price', '')})\n\n"
        f"<i>Запиши голосовое сообщение (или видео-кружочек):</i>\n"
        f"1. Назови точный состав и базу блюда/напитка\n"
        f"2. Опиши баланс вкуса / технологию\n"
        f"3. Расскажи подачу, фишку и что говорить гостю\n\n"
        f"⏳ Нажми на микрофон в Telegram и наговори ответ прямо сюда 👇"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛑 Прервать экзамен", callback_data="voice_exam:abort")]
    ])

    await message.answer(text, reply_markup=kb, parse_mode="HTML")

@router.message(VoiceExamState.recording, F.voice | F.video_note)
async def process_voice_ticket(message: Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    session = active_recordings.get(user_id)

    if not session:
        await message.answer("Сессия экзамена не найдена. Начните заново через меню.")
        await state.clear()
        return

    voice_file_id = message.voice.file_id if message.voice else message.video_note.file_id
    is_video = message.video_note is not None

    cur_idx = session['index']
    item_id = session['item_ids'][cur_idx]
    exam_id = session['exam_id']

    await save_voice_submission(exam_id, item_id, cur_idx + 1, voice_file_id)

    session['index'] += 1

    if session['index'] < session['total']:
        await message.answer(f"✅ Билет {cur_idx + 1} сохранён!")
        await send_ticket_prompt(message, user_id)
    else:
        # Completed all tickets
        await state.clear()
        del active_recordings[user_id]
        await update_assigned_exam_status(exam_id, 'submitted')

        user = await get_user(user_id)
        exam = await get_assigned_exam(exam_id)

        finish_text = (
            "🎉 <b>ВСЕ БИЛЕТЫ ЗАПИСАНЫ!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"Вы успешно ответили на все {exam['ticket_count']} билетов голосового экзамена.\n"
            "Записи отправлены менеджеру бара на прослушивание и оценку.\n\n"
            "Как только менеджер проверит экзамен, вам придёт официальный вердикт!"
        )
        await message.answer(finish_text, parse_mode="HTML")

        # Notify Manager
        manager_id = exam['assigned_by']
        manager_msg = (
            f"🚨 <b>СТАЖЁР СДАЛ ГОЛОСОВОЙ ЭКЗАМЕН!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Сотрудник: <b>{user['full_name']}</b> (@{user['username'] or '—'})\n"
            f"Раздел: <b>{exam['category']}</b>\n"
            f"Билетов записано: <b>{exam['ticket_count']}</b>\n\n"
            f"Нажмите кнопку ниже, чтобы прослушать ответы и выставить оценки:"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎧 Проверить билеты стажёра", callback_data=f"voice_review:start:{exam_id}")]
        ])
        try:
            await bot.send_message(manager_id, manager_msg, reply_markup=kb, parse_mode="HTML")
        except Exception:
            pass

@router.callback_query(F.data == "voice_exam:abort")
async def cb_abort_voice(call: CallbackQuery, state: FSMContext):
    user_id = call.from_user.id
    if user_id in active_recordings:
        del active_recordings[user_id]
    await state.clear()
    await call.message.edit_text("🛑 Голосовой экзамен прерван. Вы сможете продолжить его в любое время из меню.", parse_mode="HTML")
    await call.answer()

# --- MANAGER REVIEW FLOW ---

@router.callback_query(F.data.startswith("voice_review:start:"))
async def cb_start_review(call: CallbackQuery, bot: Bot):
    exam_id = int(call.data.split(":")[2])
    submissions = await get_voice_submissions(exam_id)

    if not submissions:
        await call.answer("Ответы стажёра не найдены", show_alert=True)
        return

    # Find first ungraded submission
    first_ungraded = next((s for s in submissions if s['grade'] is None), submissions[0])
    await send_manager_ticket_review(call.message, first_ungraded, exam_id, bot)
    await call.answer()

async def send_manager_ticket_review(message: Message, submission: dict, exam_id: int, bot: Bot):
    exam = await get_assigned_exam(exam_id)
    user = await get_user(exam['user_id'])
    item = await get_item(submission['item_id'])

    caption = (
        f"🎧 <b>ПРОВЕРКА БИЛЕТА {submission['ticket_num']} из {exam['ticket_count']}</b>\n"
        f"Стажёр: <b>{user['full_name']}</b> (@{user['username'] or '—'})\n"
        f"Позиция: <b>{item['name']}</b> ({item.get('price', '')})\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📖 <b>ЭТАЛОН ДЛЯ СВЕРКИ:</b>\n"
        f"• <b>Состав:</b> {item.get('composition', '')}\n"
    )
    if item['category'] == 'cocktails':
        caption += f"• <b>Баланс & Вкус:</b> {item.get('balance', '')} | {item.get('taste', '')}\n"
    else:
        caption += f"• <b>Аллергены:</b> {item.get('allergens', '')}\n"

    caption += f"• <b>Подача & Скрипт:</b> <i>{item.get('pitch_script', '')[:150]}...</i>"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🟢 Зачёт (+1)", callback_data=f"voice_grade:{submission['id']}:1:{exam_id}"),
            InlineKeyboardButton(text="🔴 Незачёт (0)", callback_data=f"voice_grade:{submission['id']}:0:{exam_id}")
        ]
    ])

    try:
        await bot.send_voice(
            chat_id=message.chat.id,
            voice=submission['voice_file_id'],
            caption=caption,
            reply_markup=kb,
            parse_mode="HTML"
        )
    except Exception:
        # In case it's a video note
        await bot.send_video_note(
            chat_id=message.chat.id,
            video_note=submission['voice_file_id'],
            reply_markup=kb
        )
        await bot.send_message(
            chat_id=message.chat.id,
            text=caption,
            reply_markup=kb,
            parse_mode="HTML"
        )

@router.callback_query(F.data.startswith("voice_grade:"))
async def cb_grade_ticket(call: CallbackQuery, bot: Bot):
    parts = call.data.split(":")
    submission_id = int(parts[1])
    grade = int(parts[2])
    exam_id = int(parts[3])

    await grade_voice_submission(submission_id, grade, call.from_user.id)
    await call.answer("Оценка сохранена!")

    # Check if all completed
    is_completed, score, total, pct = await check_exam_grading_completed(exam_id)

    if is_completed:
        exam = await get_assigned_exam(exam_id)
        user = await get_user(exam['user_id'])
        status = "🟢 СДАНО" if pct >= 80 else "🔴 НЕ СДАНО"

        manager_finish_text = (
            f"✅ <b>ЭКЗАМЕН ПОЛНОСТЬЮ ПРОВЕРЕН!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Сотрудник: <b>{user['full_name']}</b> (@{user['username'] or '—'})\n"
            f"Итоговый балл: <b>{score} из {total} ({pct}%)</b>\n"
            f"Вердикт: <b>{status}</b>\n\n"
            f"Официальный результат автоматически отправлен стажёру в чат."
        )
        await call.message.answer(manager_finish_text, parse_mode="HTML")

        # Notify Trainee
        trainee_msg = (
            f"📋 <b>ВАШ ГОЛОСОВОЙ ЭКЗАМЕН ПРОВЕРЕН МЕНЕДЖЕРОМ!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Результат: <b>{score} из {total} билетов ({pct}%)</b>\n\n"
            f"Вердикт: <b>{status}</b>\n"
        )
        if pct >= 80:
            trainee_msg += "🎉 Поздравляем! Допуск к смене успешно получен!"
        else:
            trainee_msg += "⚠️ Нужно дополнительно подучить рецептуры и подачу. Повторите позиции в тренажёре."

        try:
            await bot.send_message(user['user_id'], trainee_msg, parse_mode="HTML")
        except Exception:
            pass
    else:
        # Show next ungraded ticket
        submissions = await get_voice_submissions(exam_id)
        next_ungraded = next((s for s in submissions if s['grade'] is None), None)
        if next_ungraded:
            await send_manager_ticket_review(call.message, next_ungraded, exam_id, bot)
