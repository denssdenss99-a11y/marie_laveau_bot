from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from database.db import get_or_create_user, get_user_stats, get_user
from keyboards.reply import get_main_reply_kb
from config import ADMIN_IDS

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username
    full_name = message.from_user.full_name

    user = await get_or_create_user(user_id, username, full_name, ADMIN_IDS)
    is_admin = bool(user and user.get('role') in ('admin', 'manager', 'spider_man')) or user_id in ADMIN_IDS

    welcome_text = (
        f"🔮 <b>Добро пожаловать в Marie Laveau Staff Bot!</b>\n\n"
        f"Привет, {message.from_user.first_name}! Этот бот создан для быстрого и удобного изучения меню бара "
        f"<b>Marie Laveau</b> (коктейльная карта, креольская кухня, регламенты подачи и легенды).\n\n"
        f"<b>Разделы бота:</b>\n"
        f"• 🎓 <b>Тренажёр</b> — флеш-карточки со смарт-повторением (Активное воспоминание)\n"
        f"• 📝 <b>Сдать экзамен</b> — тестовый срез знаний из 15 вопросов для допуска к смене\n"
        f"• 📖 <b>База знаний</b> — полный каталог и поиск по блюдам и коктейлям\n"
        f"• 📜 <b>Шпаргалка</b> — легенда Marie Laveau, стандарты сервиса, ритуалы и аллергены\n"
        f"• 👤 <b>Мой профиль</b> — статистика твоего прогресса\n\n"
        f"Выбирай нужный раздел в меню ниже 👇"
    )

    await message.answer(
        welcome_text,
        reply_markup=get_main_reply_kb(is_admin=is_admin),
        parse_mode="HTML"
    )

@router.message(F.text == "👤 Мой профиль")
async def show_profile(message: Message):
    user_id = message.from_user.id
    user = await get_user(user_id)
    if not user:
        user = await get_or_create_user(user_id, message.from_user.username, message.from_user.full_name, ADMIN_IDS)

    stats = await get_user_stats(user_id)
    if user_id == 1368643174 or user.get('role') == 'spider_man':
        role_badge = "🕷 Человек-паук"
    elif user.get('role') in ('admin', 'manager'):
        role_badge = "👑 Менеджер / Админ"
    else:
        role_badge = "🎓 Стажёр"

    best_score_text = f"{stats['best_exam_score']}%" if stats['best_exam_score'] is not None else "Ещё не сдавался"

    text = (
        f"👤 <b>ПРОФИЛЬ СОТРУДНИКА</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Имя: <b>{user['full_name']}</b> (@{user['username'] or '—'})\n"
        f"Статус: <b>{role_badge}</b>\n\n"
        f"📊 <b>Общий прогресс изучения:</b>\n"
        f"• Изучено позиций: <b>{stats['studied']}</b> из {stats['total_items']}\n"
        f"  └ 🟢 Освоено на отлично (Box 3): <b>{stats['mastered']}</b>\n"
        f"  └ 🟡 В процессе (Box 2): <b>{stats['learning']}</b>\n"
        f"  └ 🔴 Требуют повторения (Box 1): <b>{stats['struggling']}</b>\n\n"
        f"🍸 <b>Коктейли:</b> изучено {stats['cocktails_studied']} / {stats['total_cocktails']} "
        f"(на отлично: {stats['cocktails_mastered']})\n"
        f"🍲 <b>Кухня:</b> изучено {stats['food_studied']} / {stats['total_food']} "
        f"(на отлично: {stats['food_mastered']})\n\n"
        f"📝 <b>Экзамены:</b>\n"
        f"• Сдано экзаменов: <b>{stats['exams_count']}</b>\n"
        f"• Лучший результат: <b>{best_score_text}</b>\n"
        f"• Успешных ответов: <b>{stats['total_known']}</b> | Ошибок: <b>{stats['total_mistakes']}</b>"
    )

    await message.answer(text, parse_mode="HTML")

@router.callback_query(F.data == "main_menu")
async def cb_main_menu(call: CallbackQuery):
    await call.message.delete()
    user = await get_user(call.from_user.id)
    is_admin = bool(user and user.get('role') in ('admin', 'manager', 'spider_man')) or call.from_user.id in ADMIN_IDS
    await call.message.answer(
        "🔮 Главное меню Marie Laveau Staff Bot:",
        reply_markup=get_main_reply_kb(is_admin=is_admin)
    )
    await call.answer()
