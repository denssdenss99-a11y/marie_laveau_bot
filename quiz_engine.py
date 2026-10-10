import random
import re
from database.db import get_all_items

def parse_ingredients(text: str) -> list:
    # Remove text in parentheses first, e.g. (62°C, Medium), (тунец в с/с, домашний майонез...)
    clean = re.sub(r'\(.*?\)', '', text or '')
    raw = re.split(r'[,;\n]', clean)
    cleaned = []
    seen = set()
    for r in raw:
        item = r.strip().rstrip('.')
        if 2 < len(item) < 55 and not any(k in item.lower() for k in ['состав:', 'подаем', 'подается', 'сверху', 'обжарен']):
            lx = item.lower()
            if lx not in seen:
                seen.add(lx)
                cleaned.append(item)
    return cleaned

async def generate_self_exam(category: str = 'all', count: int = 10) -> list:
    """
    Generates a list of questions alternating between:
    - 'builder': Интерактивный конструктор «Собери состав»
    - 'imposter': «Найди лишний ингредиент»
    """
    items = await get_all_items(category if category in ('cocktails', 'food') else None)
    if not items:
        return []

    # Build ingredient pool for distractors
    pool = []
    for it in items:
        ingrs = parse_ingredients(it['composition'])
        pool.extend(ingrs)
    pool = list(set(pool))

    # Pick items for questions
    chosen_items = random.sample(items, min(count, len(items)))
    questions = []

    for idx, item in enumerate(chosen_items):
        real_ingrs = parse_ingredients(item['composition'])
        # Fallback if too few ingredients
        if len(real_ingrs) < 2:
            real_ingrs = [item['name']]

        # Alternate between builder and imposter
        q_type = 'builder' if idx % 2 == 0 else 'imposter'

        if q_type == 'builder' and len(real_ingrs) >= 2:
            # Pick 2-3 real ingredients
            num_real = min(3, len(real_ingrs))
            selected_real = random.sample(real_ingrs, num_real)

            # Pick 3 distractors so total 5-6 options fit vertically and horizontally
            other_pool = [x for x in pool if x.lower() not in [r.lower() for r in real_ingrs]]
            num_distractors = min(3, len(other_pool))
            distractors = random.sample(other_pool, num_distractors) if other_pool else ["Мята", "Сок лайма"]

            all_opts = [{"text": r, "correct": True} for r in selected_real] + \
                       [{"text": d, "correct": False} for d in distractors]
            random.shuffle(all_opts)

            questions.append({
                'q_num': idx + 1,
                'type': 'builder',
                'item_id': item['id'],
                'item_name': item['name'],
                'category': item['category'],
                'subcategory': item.get('subcategory', ''),
                'full_composition': item.get('composition', ''),
                'options': all_opts,
                'target_count': num_real
            })
        else:
            # Imposter question
            num_real = min(3, len(real_ingrs))
            selected_real = random.sample(real_ingrs, num_real)

            other_pool = [x for x in pool if x.lower() not in [r.lower() for r in real_ingrs]]
            imposter = random.choice(other_pool) if other_pool else "Соус чимичурри"

            all_opts = [{"text": r, "is_imposter": False} for r in selected_real] + \
                       [{"text": imposter, "is_imposter": True}]
            random.shuffle(all_opts)

            questions.append({
                'q_num': idx + 1,
                'type': 'imposter',
                'item_id': item['id'],
                'item_name': item['name'],
                'category': item['category'],
                'subcategory': item.get('subcategory', ''),
                'full_composition': item.get('composition', ''),
                'imposter': imposter,
                'options': all_opts
            })

    return questions
