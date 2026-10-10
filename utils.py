import os
import json
import logging

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')

def load_guides() -> list:
    candidates = [
        os.path.join(DATA_DIR, 'guides.json'),
        os.path.join(BASE_DIR, 'data', 'guides.json'),
        os.path.abspath(os.path.join(os.getcwd(), 'data', 'guides.json')),
        os.path.abspath('data/guides.json'),
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list) and len(data) > 0:
                        return data
            except Exception as e:
                logger.error(f"Error reading {path}: {e}")

    try:
        from data.guides_defaults import GUIDES
        if GUIDES:
            return GUIDES
    except Exception as e:
        logger.error(f"Error loading fallback guides: {e}")

    return []

def format_card_question(item: dict, is_exam: bool = False, current_q: int = 1, total_q: int = 15) -> str:
    category = item.get('category')
    name = item.get('name')
    subcat = item.get('subcategory', '')
    note = item.get('note', '')

    header_badge = f"📝 ЭКЗАМЕН ({current_q}/{total_q})" if is_exam else "🎓 ТРЕНАЖЁР"

    if category == 'cocktails':
        text = (
            f"<b>{header_badge} | 🍸 КОКТЕЙЛИ</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📍 <b>Позиция:</b> <code>{name}</code>\n"
        )
        if note:
            text += f"<i>{note}</i>\n"
        text += (
            f"\n🧠 <i>Вспомни:</i>\n"
            f"• Состав и ключевые ингредиенты\n"
            f"• Крепость, баланс и вкусовые дескрипторы\n"
            f"• Подачу и легенду («Что говорить гостю»)"
        )
    else:
        text = (
            f"<b>{header_badge} | 🍲 КУХНЯ ({subcat})</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📍 <b>Блюдо:</b> <code>{name}</code>\n"
            f"\n🧠 <i>Вспомни:</i>\n"
            f"• Состав, заправки и соусы\n"
            f"• Технологию (су-вид, фритюр, прожарку)\n"
            f"• Аллергены и нюансы для гостей"
        )
    return text

def format_card_answer(item: dict, is_exam: bool = False, current_q: int = 1, total_q: int = 15) -> str:
    category = item.get('category')
    name = item.get('name')
    price = item.get('price', '')
    comp = item.get('composition', '')
    pitch = item.get('pitch_script', '')

    header_badge = f"📝 ЭКЗАМЕН ({current_q}/{total_q})" if is_exam else "🎓 ТРЕНАЖЁР"

    if category == 'cocktails':
        balance = item.get('balance', '')
        taste = item.get('taste', '')
        strength = item.get('strength', '')

        text = (
            f"<b>{header_badge} | 🍸 ОТВЕТ</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"✨ <b>{name}</b> ({price})\n\n"
            f"🥣 <b>Состав:</b>\n{comp}\n\n"
            f"⚖️ <b>Баланс & Вкус:</b>\n"
            f"• Баланс: {balance}\n"
            f"• Крепость: {strength}\n"
            f"• Вкус: {taste}\n\n"
            f"🎙 <b>Что говорить гостю & Подача:</b>\n"
            f"<i>{pitch}</i>"
        )
    else:
        subcat = item.get('subcategory', '')
        details = item.get('details', '')
        allergens = item.get('allergens', '')

        text = (
            f"<b>{header_badge} | 🍲 ОТВЕТ</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"✨ <b>{name}</b> ({price})\n"
            f"Раздел: <i>{subcat}</i>\n\n"
            f"🥣 <b>Состав:</b>\n{comp}\n\n"
            f"👨‍🍳 <b>Технология & Подача:</b>\n{details}\n\n"
            f"⚠️ <b>Аллергены:</b>\n<b>{allergens}</b>\n\n"
            f"🎙 <b>Как презентовать:</b>\n<i>{pitch}</i>"
        )
    return text

def format_item_detail(item: dict) -> str:
    return format_card_answer(item, is_exam=False)
