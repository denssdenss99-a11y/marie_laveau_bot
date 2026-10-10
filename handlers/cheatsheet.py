from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from keyboards.inline import get_guides_menu_kb, get_guide_detail_kb
from utils import load_guides

router = Router()

@router.message(F.text == "📜 Шпаргалка")
async def show_guides_menu(message: Message):
    guides = load_guides()
    text = (
        "📜 <b>ШПАРГАЛКА И СТАНДАРТЫ MARIE LAVEAU</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Официальная база знаний и регламенты сервиса бара.\n"
        "Выбери интересующую инструкцию:"
    )
    await message.answer(text, reply_markup=get_guides_menu_kb(guides), parse_mode="HTML")

@router.callback_query(F.data == "guides:home")
async def cb_guides_home(call: CallbackQuery):
    guides = load_guides()
    text = (
        "📜 <b>ШПАРГАЛКА И СТАНДАРТЫ MARIE LAVEAU</b>\n"
        "Выбери раздел:"
    )
    await call.message.edit_text(text, reply_markup=get_guides_menu_kb(guides), parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data.startswith("guide:"))
async def cb_view_guide(call: CallbackQuery):
    guide_id = call.data.split(":")[1]
    guides = load_guides()
    guide = next((g for g in guides if g['id'] == guide_id), None)

    if not guide:
        await call.answer("Инструкция не найдена", show_alert=True)
        return

    text = guide['content']
    kb = get_guide_detail_kb()
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()
