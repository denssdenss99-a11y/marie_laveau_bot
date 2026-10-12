from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from database.db import (
    get_user,
    get_all_users,
    get_manager_analytics,
    get_connection,
    import_initial_data,
    is_user_banned,
    ban_user,
    unban_user,
    get_banned_users,
    get_banned_user_by_id,
    delete_user_data,
    set_user_role
)
from keyboards.inline import (
    get_admin_menu_kb,
    get_admin_bans_menu_kb,
    get_banned_user_card_kb
)
from config import ADMIN_IDS

router = Router()

class AdminBanState(StatesGroup):
    waiting_for_user_identifier = State()

async def is_user_admin(user_id: int) -> bool:
    if user_id in ADMIN_IDS:
        return True
    user = await get_user(user_id)
    return bool(user and user['role'] in ('admin', 'manager', 'spider_man'))

def get_user_role_display(u: dict) -> str:
    if u['user_id'] == 1368643174 or u.get('role') == 'spider_man':
        return "🕷 Человек-паук"
    elif u.get('role') == 'banned' or u.get('is_banned'):
        return "🚫 Заблокирован"
    elif u.get('role') in ('admin', 'manager'):
        return "👑 Администратор"
    return "🎓 Стажёр"

def get_user_role_icon(u: dict) -> str:
    if u['user_id'] == 1368643174 or u.get('role') == 'spider_man':
        return "🕷"
    elif u.get('role') == 'banned' or u.get('is_banned'):
        return "🚫"
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
        is_banned = user.get('role') == 'banned' or await is_user_banned(user_id=target_user_id)
        if is_banned:
            role_title = "🚫 Заблокирован (В чёрном списке)"
        elif user['role'] in ('admin', 'manager'):
            role_title = "👑 Администратор / Менеджер"
        else:
            role_title = "🎓 Стажёр"

        text = (
            f"👤 <b>Настройка доступа: {user['full_name']}</b> (@{user['username'] or '—'})\n"
            f"ID: <code>{user['user_id']}</code>\n"
            f"Текущий статус: <b>{role_title}</b>\n\n"
            f"Выберите действие для этого пользователя:"
        )
        buttons = []
        if is_banned:
            buttons.append([InlineKeyboardButton(text="🟢 Разблокировать (Сделать стажёром)", callback_data=f"admin:unban_user:{target_user_id}")])
        else:
            buttons.append([InlineKeyboardButton(text="👑 Сделать Администратором", callback_data=f"admin:set_role:{target_user_id}:admin")])
            buttons.append([InlineKeyboardButton(text="🎓 Сделать Стажёром", callback_data=f"admin:set_role:{target_user_id}:trainee")])
            buttons.append([InlineKeyboardButton(text="🚫 Заблокировать (В Чёрный список)", callback_data=f"admin:ban_user:{target_user_id}")])

        buttons.append([InlineKeyboardButton(text="🗑 Удалить из базы данных", callback_data=f"admin:delete_user:{target_user_id}")])
        buttons.append([InlineKeyboardButton(text="↩️ К списку сотрудников", callback_data="admin:roles:list")])

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
async def cb_admin_menu_back(call: CallbackQuery, state: FSMContext = None):
    if state:
        await state.clear()
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

# ==================== БЛОКИРОВКИ И ЧЁРНЫЙ СПИСОК ====================

@router.callback_query(F.data.startswith("admin:ban_user:"))
async def cb_admin_ban_user_direct(call: CallbackQuery):
    if not await is_user_admin(call.from_user.id):
        await call.answer("Доступ запрещён", show_alert=True)
        return

    target_user_id = int(call.data.split(":")[2])
    if target_user_id == 1368643174:
        await call.answer("🕷 Нельзя заблокировать Создателя!", show_alert=True)
        return
    if target_user_id == call.from_user.id:
        await call.answer("⛔ Вы не можете заблокировать самого себя!", show_alert=True)
        return

    target_user = await get_user(target_user_id)
    uname = target_user['username'] if target_user else None

    await ban_user(
        user_id=target_user_id,
        username=uname,
        banned_by=call.from_user.id,
        reason="Заблокирован через карточку пользователя"
    )
    await call.answer("🚫 Пользователь внесён в чёрный список!", show_alert=True)
    await cb_admin_roles_user(call)

@router.callback_query(F.data.startswith("admin:unban_user:"))
async def cb_admin_unban_user_direct(call: CallbackQuery):
    if not await is_user_admin(call.from_user.id):
        await call.answer("Доступ запрещён", show_alert=True)
        return

    target_user_id = int(call.data.split(":")[2])
    await unban_user(user_id=target_user_id)
    await call.answer("🟢 Пользователь успешно разблокирован!", show_alert=True)
    await cb_admin_roles_user(call)

@router.callback_query(F.data.startswith("admin:delete_user:"))
async def cb_admin_delete_user_ask(call: CallbackQuery):
    if not await is_user_admin(call.from_user.id):
        await call.answer("Доступ запрещён", show_alert=True)
        return

    target_user_id = int(call.data.split(":")[2])
    if target_user_id == 1368643174:
        await call.answer("🕷 Нельзя удалить Создателя!", show_alert=True)
        return

    user = await get_user(target_user_id)
    name = user['full_name'] if user else f"ID {target_user_id}"

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    text = (
        f"⚠️ <b>ВНИМАНИЕ! ПОДТВЕРЖДЕНИЕ УДАЛЕНИЯ</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Вы действительно хотите полностью удалить пользователя <b>{name}</b>?\n\n"
        f"Будут безвозвратно стёрты:\n"
        f"• Профиль сотрудника\n"
        f"• Прогресс тренажёра и флеш-карточек\n"
        f"• История всех сданных экзаменов и голосовых ответов\n\n"
        f"<i>Это действие необратимо!</i>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Да, удалить навсегда", callback_data=f"admin:delete_confirm:{target_user_id}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data=f"admin:roles:user:{target_user_id}")]
    ])
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data.startswith("admin:delete_confirm:"))
async def cb_admin_delete_user_confirm(call: CallbackQuery):
    if not await is_user_admin(call.from_user.id):
        await call.answer("Доступ запрещён", show_alert=True)
        return

    target_user_id = int(call.data.split(":")[2])
    if target_user_id == 1368643174:
        await call.answer("🕷 Нельзя удалить Создателя!", show_alert=True)
        return

    await delete_user_data(target_user_id)
    await call.answer("🗑 Пользователь успешно удалён из базы данных!", show_alert=True)
    await cb_admin_roles_list(call)

@router.callback_query(F.data == "admin:bans:menu")
async def cb_admin_bans_menu(call: CallbackQuery, state: FSMContext = None):
    if not await is_user_admin(call.from_user.id):
        await call.answer("Доступ запрещён", show_alert=True)
        return

    if state:
        await state.clear()

    banned_list = await get_banned_users()
    count = len(banned_list)

    text = (
        "🚫 <b>УПРАВЛЕНИЕ ЧЁРНЫМ СПИСКОМ (БАН)</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"Текущее количество заблокированных: <b>{count}</b>\n\n"
        "Заблокированные пользователи не имеют доступа к тренажёру, экзаменам, "
        "базе знаний и шпаргалкам бара.\n\n"
        "Вы можете заблокировать постороннего человека по его <b>Telegram ID</b> или <b>@username</b>, "
        "либо выбрать сотрудника из списка пользователей."
    )
    await call.message.edit_text(text, reply_markup=get_admin_bans_menu_kb(count), parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data == "admin:bans:list")
async def cb_admin_bans_list(call: CallbackQuery):
    if not await is_user_admin(call.from_user.id):
        await call.answer("Доступ запрещён", show_alert=True)
        return

    banned_list = await get_banned_users()
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    if not banned_list:
        text = (
            "📋 <b>ЧЁРНЫЙ СПИСОК ПУСТ</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "В данный момент нет ни одного заблокированного пользователя."
        )
        buttons = [
            [InlineKeyboardButton(text="➕ Заблокировать по ID / @username", callback_data="admin:bans:add")],
            [InlineKeyboardButton(text="↩️ В меню блокировок", callback_data="admin:bans:menu")]
        ]
        await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")
        await call.answer()
        return

    text = (
        "📋 <b>СПИСОК ЗАБЛОКИРОВАННЫХ ПОЛЬЗОВАТЕЛЕЙ</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Нажмите на пользователя для просмотра деталей или разблокировки:\n\n"
    )
    buttons = []
    for b in banned_list[:25]:
        uname = f"@{b['username']}" if b['username'] else "нет username"
        uid_str = f"ID: {b['user_id']}" if b['user_id'] else "ID: —"
        name_str = f" ({b['full_name']})" if b.get('full_name') else ""
        button_label = f"🚫 {uname} [{uid_str}]{name_str}"
        buttons.append([InlineKeyboardButton(
            text=button_label[:42],
            callback_data=f"admin:bans:view:{b['id']}"
        )])

    buttons.append([InlineKeyboardButton(text="➕ Заблокировать ещё", callback_data="admin:bans:add")])
    buttons.append([InlineKeyboardButton(text="↩️ В меню блокировок", callback_data="admin:bans:menu")])

    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data.startswith("admin:bans:view:"))
async def cb_admin_bans_view(call: CallbackQuery):
    if not await is_user_admin(call.from_user.id):
        await call.answer("Доступ запрещён", show_alert=True)
        return

    ban_id = int(call.data.split(":")[3])
    b = await get_banned_user_by_id(ban_id)
    if not b:
        await call.answer("Запись не найдена", show_alert=True)
        return

    uname = f"@{b['username']}" if b['username'] else "—"
    uid_str = str(b['user_id']) if b['user_id'] else "—"
    name_str = b['full_name'] if b.get('full_name') else "—"
    date_str = str(b.get('created_at', ''))[:16]

    text = (
        f"🚫 <b>КАРТОЧКА БЛОКИРОВКИ #{b['id']}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"• Telegram ID: <code>{uid_str}</code>\n"
        f"• Username: <b>{uname}</b>\n"
        f"• Имя в базе: <b>{name_str}</b>\n"
        f"• Причина: <i>{b.get('reason') or 'Не указана'}</i>\n"
        f"• Дата бана: <b>{date_str}</b>\n"
    )

    await call.message.edit_text(text, reply_markup=get_banned_user_card_kb(ban_id, b.get('user_id')), parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data.startswith("admin:bans:unban:"))
async def cb_admin_bans_unban(call: CallbackQuery):
    if not await is_user_admin(call.from_user.id):
        await call.answer("Доступ запрещён", show_alert=True)
        return

    ban_id = int(call.data.split(":")[3])
    await unban_user(ban_id=ban_id)
    await call.answer("🟢 Пользователь успешно разблокирован!", show_alert=True)
    await cb_admin_bans_list(call)

@router.callback_query(F.data == "admin:bans:add")
async def cb_admin_bans_add(call: CallbackQuery, state: FSMContext):
    if not await is_user_admin(call.from_user.id):
        await call.answer("Доступ запрещён", show_alert=True)
        return

    await state.set_state(AdminBanState.waiting_for_user_identifier)
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    text = (
        "🚫 <b>БЛОКИРОВКА ПОЛЬЗОВАТЕЛЯ</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Отправьте сообщением <b>Telegram ID</b> (цифры) или <b>@username</b> человека, "
        "которого хотите заблокировать.\n\n"
        "<i>Примеры:</i>\n"
        "• <code>123456789</code>\n"
        "• <code>@username_user</code>\n\n"
        "После этого бот мгновенно ограничит доступ данному человеку ко всем функциям."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin:bans:menu")]
    ])
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()

@router.message(AdminBanState.waiting_for_user_identifier)
async def msg_admin_ban_input(message: Message, state: FSMContext):
    if not await is_user_admin(message.from_user.id):
        await state.clear()
        return

    raw_text = (message.text or '').strip()
    if raw_text.lower() in ('/cancel', 'отмена', 'назад'):
        await state.clear()
        banned_list = await get_banned_users()
        await message.answer("❌ Блокировка отменена.", reply_markup=get_admin_bans_menu_kb(len(banned_list)))
        return

    user_id = None
    username = None

    if raw_text.startswith('@'):
        username = raw_text.lstrip('@')
    elif raw_text.isdigit():
        user_id = int(raw_text)
    else:
        username = raw_text

    if user_id == 1368643174:
        await message.answer("🕷 <b>Нельзя заблокировать Человека-паука (Создателя)!</b>", parse_mode="HTML")
        await state.clear()
        return

    if user_id == message.from_user.id:
        await message.answer("⛔ <b>Вы не можете заблокировать самого себя!</b>", parse_mode="HTML")
        await state.clear()
        return

    ok, res_msg = await ban_user(
        user_id=user_id,
        username=username,
        banned_by=message.from_user.id,
        reason="Заблокирован администратором вручную"
    )

    await state.clear()
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Список заблокированных", callback_data="admin:bans:list")],
        [InlineKeyboardButton(text="➕ Заблокировать ещё", callback_data="admin:bans:add")],
        [InlineKeyboardButton(text="↩️ В админ-меню", callback_data="admin:menu")]
    ])

    if ok:
        target_display = f"ID: <code>{user_id}</code>" if user_id else f"@{username}"
        await message.answer(
            f"✅ <b>Пользователь успешно заблокирован!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Идентификатор: {target_display}\n"
            f"Пользователь внесён в чёрный список и больше не имеет доступа к боту.",
            reply_markup=kb,
            parse_mode="HTML"
        )
    else:
        await message.answer(f"⚠️ Ошибка при блокировке: {res_msg}", reply_markup=kb)

