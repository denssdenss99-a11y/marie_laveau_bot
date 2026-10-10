from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from database.db import (
    get_user,
    get_all_users,
    get_manager_analytics,
    get_connection,
    import_initial_data
)
from keyboards.inline import get_admin_menu_kb
from config import ADMIN_IDS

router = Router()

async def is_user_admin(user_id: int) -> bool:
    if user_id in ADMIN_IDS:
        return True
    user = await get_user(user_id)
    return bool(user and user['role'] in ('admin', 'manager', 'spider_man'))

def get_user_role_display(u: dict) -> str:
    if u['user_id'] == 1368643174 or u.get('role') == 'spider_man':
        return "🕷 Человек-паук"
    elif u.get('role') in ('admin', 'manager'):
        return "👑 Администратор"
    return "🎓 Стажёр"

def get_user_role_icon(u: dict) -> str:
    if u['user_id'] == 1368643174 or u.get('role') == 'spider_man':
        return "🕷"
    elif u.get('role') in ('admin', 'manager'):
        return "👑"
    return "🎓"

@router.message(F.text == "⚙️ Панель управления")
@router.message(Command("admin"))
async def open_admin_panel(message: Message):
    if not await is_user_admin(message.from_user.id):
        await message.answer("⛔ У вас нет доступа к панели менеджера.")
        return

    text = (
        "⚙️ <b>ПАНЕЛЬ УПРАВЛЕНИЯ ОБУЧЕНИЕМ (МЕНЕДЖЕР)</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Добро пожаловать в админ-панель бара Marie Laveau.\n\n"
        "Здесь вы можете отслеживать успеваемость стажёров, просматривать результаты экзаменов "
        "и видеть «слепые зоны» меню команды."
    )
    await message.answer(text, reply_markup=get_admin_menu_kb(), parse_mode="HTML")

@router.callback_query(F.data == "admin:users")
async def cb_admin_users(call: CallbackQuery):
    if not await is_user_admin(call.from_user.id):
        await call.answer("Доступ запрещён", show_alert=True)
        return

    users = await get_all_users()
    if not users:
        await call.answer("Пользователи не зарегистрированы", show_alert=True)
        return

    text = "👥 <b>СПИСОК СОТРУДНИКОВ И ПРОГРЕСС</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
    for idx, u in enumerate(users[:15]):
        uname = f"@{u['username']}" if u['username'] else "нет username"
        best_sc = f"{u['best_exam_score']}%" if u['best_exam_score'] is not None else "—"
        role_label = get_user_role_display(u)
        text += (
            f"<b>{idx+1}. {u['full_name']}</b> ({uname})\n"
            f"   • Роль: <b>{role_label}</b> | Изучено: <b>{u['studied_count']}</b> (Освоено: {u['mastered_count']})\n"
            f"   • Ошибок в тренажёре: {u['total_mistakes'] or 0}\n"
            f"   • Экзаменов: {u['exams_count']} (Лучший: <b>{best_sc}</b>)\n\n"
        )

    await call.message.edit_text(text, reply_markup=get_admin_menu_kb(), parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data == "admin:analytics")
async def cb_admin_analytics(call: CallbackQuery):
    if not await is_user_admin(call.from_user.id):
        await call.answer("Доступ запрещён", show_alert=True)
        return

    data = await get_manager_analytics()

    text = (
        "📊 <b>АНАЛИТИКА ОШИБОК («СЛЕПЫЕ ЗОНЫ»)</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Позиции меню, на которых команда чаще всего спотыкается:\n\n"
        "🍸 <b>Топ-5 сложных коктейлей:</b>\n"
    )
    if data['top_cocktails']:
        for idx, c in enumerate(data['top_cocktails']):
            text += f"{idx+1}. {c['name']} — <b>{c['mistakes']} ошибок</b>\n"
    else:
        text += "<i>Пока нет зафиксированных ошибок.</i>\n"

    text += "\n🍲 <b>Топ-5 сложных блюд кухни:</b>\n"
    if data['top_food']:
        for idx, f in enumerate(data['top_food']):
            text += f"{idx+1}. {f['name']} — <b>{f['mistakes']} ошибок</b>\n"
    else:
        text += "<i>Пока нет зафиксированных ошибок.</i>\n"

    text += "\n💡 <i>Рекомендация: разберите эти позиции на ближайшей пятиминутке перед сменой.</i>"

    await call.message.edit_text(text, reply_markup=get_admin_menu_kb(), parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data == "admin:exams")
async def cb_admin_exams(call: CallbackQuery):
    if not await is_user_admin(call.from_user.id):
        await call.answer("Доступ запрещён", show_alert=True)
        return

    data = await get_manager_analytics()
    exams = data['recent_exams']

    text = "🏆 <b>ПОСЛЕДНИЕ СДАЧИ ЭКЗАМЕНОВ</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
    if not exams:
        text += "<i>Экзамены ещё никто не сдавал.</i>"
    else:
        for idx, e in enumerate(exams):
            uname = f"@{e['username']}" if e['username'] else e['full_name']
            status = "🟢 Сдано" if e['percentage'] >= 85 else "🔴 Не сдано"
            text += (
                f"<b>{idx+1}. {e['full_name']}</b> ({uname})\n"
                f"   • Раздел: {e['category']} | Балл: <b>{e['score']}/{e['total']} ({e['percentage']}%)</b>\n"
                f"   • Вердикт: {status} | Дата: {e['created_at'][:16]}\n\n"
            )

    await call.message.edit_text(text, reply_markup=get_admin_menu_kb(), parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data == "admin:assign:start")
async def cb_admin_assign_start(call: CallbackQuery):
    if not await is_user_admin(call.from_user.id):
        await call.answer("Доступ запрещён", show_alert=True)
        return

    users = await get_all_users()
    trainees = [u for u in users if u['user_id'] != call.from_user.id]

    if not trainees:
        await call.answer("Нет зарегистрированных сотрудников для назначения.", show_alert=True)
        return

    text = "🎯 <b>НАЗНАЧЕНИЕ ЭКЗАМЕНА</b>\nВыберите сотрудника для аттестации:"
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    buttons = []
    for u in trainees[:15]:
        uname = f"@{u['username']}" if u['username'] else u['full_name']
        buttons.append([InlineKeyboardButton(
            text=f"👤 {u['full_name']} ({uname})",
            callback_data=f"admin:assign:user:{u['user_id']}"
        )])
    buttons.append([InlineKeyboardButton(text="↩️ В админ-меню", callback_data="admin:menu")])

    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data.startswith("admin:assign:user:"))
async def cb_admin_assign_choose_cat(call: CallbackQuery):
    target_user_id = int(call.data.split(":")[3])
    target_user = await get_user(target_user_id)

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    text = (
        f"🎯 Назначение экзамена сотруднику: <b>{target_user['full_name']}</b>\n\n"
        f"Выберите раздел аттестации (будет сформировано 5 случайных билетов с голосовыми ответами):"
    )
    buttons = [
        [InlineKeyboardButton(text="🍸 Коктейли (5 билетов)", callback_data=f"admin:assign:do:{target_user_id}:cocktails")],
        [InlineKeyboardButton(text="🍲 Кухня (5 билетов)", callback_data=f"admin:assign:do:{target_user_id}:food")],
        [InlineKeyboardButton(text="🎲 Всё меню (5 билетов)", callback_data=f"admin:assign:do:{target_user_id}:all")],
        [InlineKeyboardButton(text="↩️ Отмена", callback_data="admin:assign:start")]
    ]
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data.startswith("admin:assign:do:"))
async def cb_admin_assign_execute(call: CallbackQuery, bot: Bot):
    parts = call.data.split(":")
    target_user_id = int(parts[3])
    category = parts[4]

    from database.db import create_assigned_exam
    assigned = await create_assigned_exam(
        user_id=target_user_id,
        category=category,
        assigned_by=call.from_user.id,
        ticket_count=5
    )

    if not assigned:
        await call.answer("Ошибка при создании экзамена", show_alert=True)
        return

    target_user = await get_user(target_user_id)
    cat_names = {'cocktails': 'Коктейли', 'food': 'Кухня', 'all': 'Всё меню'}
    cat_title = cat_names.get(category, category)

    # Confirm to admin
    await call.message.edit_text(
        f"✅ <b>Экзамен успешно назначен!</b>\n"
        f"Сотрудник: <b>{target_user['full_name']}</b>\n"
        f"Раздел: <b>{cat_title}</b> (5 билетов)\n\n"
        f"Бот отправил стажёру уведомление с билетами в личные сообщения.",
        reply_markup=get_admin_menu_kb(),
        parse_mode="HTML"
    )
    await call.answer()

    # Notify Trainee
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    notify_text = (
        f"🚨 <b>ВНИМАНИЕ! ВАМ НАЗНАЧЕН ГОЛОСОВОЙ ЭКЗАМЕН!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Менеджер бара назначил вам официальную аттестацию:\n"
        f"• Раздел: <b>{cat_title}</b>\n"
        f"• Количество билетов: <b>5</b>\n"
        f"• Формат: <b>Голосовые ответы (состав, баланс, презентация гостю)</b>\n\n"
        f"Нажмите кнопку ниже, чтобы приступить к записи ответов прямо сейчас 👇"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎙 Начать голосовой экзамен", callback_data=f"voice_exam:start:{assigned['id']}")]
    ])
    try:
        await bot.send_message(target_user_id, notify_text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass

@router.callback_query(F.data == "admin:roles:list")
async def cb_admin_roles_list(call: CallbackQuery):
    if not await is_user_admin(call.from_user.id):
        await call.answer("Доступ запрещён", show_alert=True)
        return

    users = await get_all_users()
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    buttons = []
    for u in users[:20]:
        role_icon = get_user_role_icon(u)
        uname = f"@{u['username']}" if u['username'] else u['full_name']
        buttons.append([InlineKeyboardButton(
            text=f"{role_icon} {u['full_name']} ({uname})",
            callback_data=f"admin:roles:user:{u['user_id']}"
        )])
    buttons.append([InlineKeyboardButton(text="↩️ В админ-меню", callback_data="admin:menu")])

    text = (
        "👑 <b>УПРАВЛЕНИЕ АДМИНИСТРАТОРАМИ И РОЛЯМИ</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Выберите сотрудника, чтобы изменить его уровень доступа:\n"
        "• 👑 <b>Администратор</b> — полный доступ к проверке экзаменов и аналитике\n"
        "• 🎓 <b>Стажёр</b> — стандартный доступ к обучению и тестам\n"
        "• 🕷 <b>Человек-паук</b> — эксклюзивная роль Создателя"
    )
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data.startswith("admin:roles:user:"))
async def cb_admin_roles_user(call: CallbackQuery):
    target_user_id = int(call.data.split(":")[3])
    user = await get_user(target_user_id)
    if not user:
        await call.answer("Пользователь не найден", show_alert=True)
        return

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    if target_user_id == 1368643174 or user.get('role') == 'spider_man':
        text = (
            f"👤 <b>Настройка доступа: {user['full_name']}</b> (@{user['username'] or '—'})\n"
            f"Текущая роль: <b>🕷 Человек-паук (Создатель)</b>\n\n"
            f"🕸 <i>С великой силой приходит великая ответственность! Роль Человека-паука закреплена эксклюзивно за тобой.</i>"
        )
        buttons = [
            [InlineKeyboardButton(text="↩️ К списку ролей", callback_data="admin:roles:list")]
        ]
    else:
        role_title = "👑 Администратор / Менеджер" if user['role'] in ('admin', 'manager') else "🎓 Стажёр"
        text = (
            f"👤 <b>Настройка доступа: {user['full_name']}</b> (@{user['username'] or '—'})\n"
            f"Текущая роль: <b>{role_title}</b>\n\n"
            f"Выберите новую роль для сотрудника:"
        )
        buttons = [
            [InlineKeyboardButton(text="👑 Сделать Администратором", callback_data=f"admin:set_role:{target_user_id}:admin")],
            [InlineKeyboardButton(text="🎓 Сделать Стажёром", callback_data=f"admin:set_role:{target_user_id}:trainee")],
            [InlineKeyboardButton(text="↩️ К списку ролей", callback_data="admin:roles:list")]
        ]
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data.startswith("admin:set_role:"))
async def cb_admin_set_role(call: CallbackQuery, bot: Bot):
    parts = call.data.split(":")
    target_user_id = int(parts[2])
    new_role = parts[3]

    if target_user_id == 1368643174:
        await call.answer("🕷 Роль Человека-паука неизменна!", show_alert=True)
        return

    from database.db import set_user_role
    await set_user_role(target_user_id, new_role)
    target_user = await get_user(target_user_id)

    role_title = "Администратором" if new_role == 'admin' else "Стажёром"
    await call.answer(f"Роль изменена на: {role_title}!", show_alert=True)

    # Re-render user view
    await cb_admin_roles_user(call)

    # Notify target user
    from keyboards.reply import get_main_reply_kb
    if new_role == 'admin':
        notify_text = (
            "🎉 <b>ПОЗДРАВЛЯЕМ! ВАМ ВЫДАНЫ ПРАВА АДМИНИСТРАТОРА!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Теперь вам доступна кнопка <b>«⚙️ Панель управления»</b>:\n"
            "• Назначение экзаменов стажёрам\n"
            "• Проверка голосовых билетов\n"
            "• Просмотр статистики и аналитики ошибок команды."
        )
        try:
            await bot.send_message(
                target_user_id,
                notify_text,
                reply_markup=get_main_reply_kb(is_admin=True),
                parse_mode="HTML"
            )
        except Exception:
            pass

@router.callback_query(F.data == "admin:menu")
async def cb_admin_menu_back(call: CallbackQuery):
    await call.message.edit_text(
        "⚙️ <b>ПАНЕЛЬ УПРАВЛЕНИЯ ОБУЧЕНИЕМ (МЕНЕДЖЕР)</b>\nВыберите действие:",
        reply_markup=get_admin_menu_kb(),
        parse_mode="HTML"
    )
    await call.answer()

@router.callback_query(F.data == "admin:reload")
async def cb_admin_reload_data(call: CallbackQuery):
    if not await is_user_admin(call.from_user.id):
        await call.answer("Доступ запрещён", show_alert=True)
        return

    async with get_connection() as db:
        await import_initial_data(db)

    await call.answer("✅ Меню успешно обновлено из JSON-файлов!", show_alert=True)
