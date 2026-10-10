import aiosqlite
import json
import os
import random
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.getenv('DATA_DIR', os.path.abspath(os.path.join(BASE_DIR, '..', 'data')))
DB_IN_DATA = os.path.join(DATA_DIR, 'marielaveau.db')
DB_IN_BASE = os.path.join(BASE_DIR, 'marielaveau.db')

if not os.path.exists(DB_IN_DATA) and os.path.exists(DB_IN_BASE):
    try:
        import shutil
        os.makedirs(DATA_DIR, exist_ok=True)
        shutil.copy(DB_IN_BASE, DB_IN_DATA)
    except Exception:
        pass

DB_PATH = DB_IN_DATA if os.path.exists(DB_IN_DATA) else DB_IN_BASE

def get_connection():
    return aiosqlite.connect(DB_PATH)

async def init_db():
    async with get_connection() as db:
        db.row_factory = aiosqlite.Row
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                role TEXT DEFAULT 'trainee',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        await db.execute('''
            CREATE TABLE IF NOT EXISTS items (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                subcategory TEXT,
                price TEXT,
                composition TEXT,
                taste TEXT,
                balance TEXT,
                strength TEXT,
                pitch_script TEXT,
                details TEXT,
                allergens TEXT,
                note TEXT
            )
        ''')

        await db.execute('''
            CREATE TABLE IF NOT EXISTS user_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                item_id TEXT NOT NULL,
                box INTEGER DEFAULT 1,
                known_count INTEGER DEFAULT 0,
                mistake_count INTEGER DEFAULT 0,
                last_reviewed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, item_id),
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (item_id) REFERENCES items(id)
            )
        ''')

        await db.execute('''
            CREATE TABLE IF NOT EXISTS exam_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                score INTEGER NOT NULL,
                total INTEGER NOT NULL,
                percentage REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')

        await db.execute('''
            CREATE TABLE IF NOT EXISTS assigned_exams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                assigned_by INTEGER NOT NULL,
                ticket_count INTEGER DEFAULT 5,
                items_json TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                score INTEGER DEFAULT 0,
                total INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                graded_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')

        await db.execute('''
            CREATE TABLE IF NOT EXISTS voice_submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                assigned_exam_id INTEGER NOT NULL,
                item_id TEXT NOT NULL,
                ticket_num INTEGER NOT NULL,
                voice_file_id TEXT NOT NULL,
                grade INTEGER,
                graded_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (assigned_exam_id) REFERENCES assigned_exams(id),
                FOREIGN KEY (item_id) REFERENCES items(id)
            )
        ''')

        await db.commit()

        # Check if items exist, if not import them
        cursor = await db.execute('SELECT COUNT(*) FROM items')
        count = (await cursor.fetchone())[0]

        if count == 0:
            await import_initial_data(db)

async def import_initial_data(db):
    cocktails_path = os.path.join(DATA_DIR, 'cocktails.json')
    food_path = os.path.join(DATA_DIR, 'food.json')

    await db.execute('DELETE FROM items')

    if os.path.exists(cocktails_path):
        with open(cocktails_path, 'r', encoding='utf-8') as f:
            cocktails = json.load(f)
            for c in cocktails:
                await db.execute('''
                    INSERT OR REPLACE INTO items (
                        id, name, category, subcategory, price, composition,
                        taste, balance, strength, pitch_script, details, allergens, note
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    c['id'], c['name'], c['category'], c.get('subcategory', 'Коктейли'),
                    c.get('price', '990 ₽'), c.get('composition', ''), c.get('taste', ''),
                    c.get('balance', ''), c.get('strength', ''), c.get('pitch_script', ''),
                    c.get('details', ''), c.get('allergens', ''), c.get('note', '')
                ))

    if os.path.exists(food_path):
        with open(food_path, 'r', encoding='utf-8') as f:
            food = json.load(f)
            for item in food:
                await db.execute('''
                    INSERT OR REPLACE INTO items (
                        id, name, category, subcategory, price, composition,
                        taste, balance, strength, pitch_script, details, allergens, note
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    item['id'], item['name'], item['category'], item.get('subcategory', 'Кухня'),
                    item.get('price', ''), item.get('composition', ''), '', '', '',
                    item.get('pitch_script', ''), item.get('details', ''), item.get('allergens', ''), ''
                ))

    await db.commit()

async def get_or_create_user(user_id: int, username: str, full_name: str, admin_ids: list = None):
    async with get_connection() as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user = await cursor.fetchone()
        
        default_role = 'spider_man' if user_id == 1368643174 else ('admin' if admin_ids and user_id in admin_ids else 'trainee')

        if not user:
            await db.execute('''
                INSERT INTO users (user_id, username, full_name, role, last_active)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (user_id, username or '', full_name or '', default_role))
            await db.commit()
            cursor = await db.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            user = await cursor.fetchone()
        else:
            await db.execute('''
                UPDATE users SET username = ?, full_name = ?, last_active = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', (username or '', full_name or '', user_id))
            if user_id == 1368643174 and user['role'] != 'spider_man':
                await db.execute("UPDATE users SET role = 'spider_man' WHERE user_id = ?", (user_id,))
            elif admin_ids and user_id in admin_ids and user['role'] not in ('admin', 'spider_man'):
                await db.execute("UPDATE users SET role = 'admin' WHERE user_id = ?", (user_id,))
            await db.commit()
            cursor = await db.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            user = await cursor.fetchone()

        return dict(user)

async def get_user(user_id: int):
    async with get_connection() as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user = await cursor.fetchone()
        return dict(user) if user else None

async def get_all_users():
    async with get_connection() as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('''
            SELECT u.*, 
                   COUNT(up.id) as studied_count,
                   SUM(CASE WHEN up.box = 3 THEN 1 ELSE 0 END) as mastered_count,
                   SUM(up.mistake_count) as total_mistakes,
                   (SELECT COUNT(*) FROM exam_results WHERE user_id = u.user_id) as exams_count,
                   (SELECT MAX(percentage) FROM exam_results WHERE user_id = u.user_id) as best_exam_score
            FROM users u
            LEFT JOIN user_progress up ON u.user_id = up.user_id
            GROUP BY u.user_id
            ORDER BY u.last_active DESC
        ''')
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

async def get_item(item_id: str):
    async with get_connection() as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('SELECT * FROM items WHERE id = ?', (item_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def get_all_items(category: str = None):
    async with get_connection() as db:
        db.row_factory = aiosqlite.Row
        if category and category != 'all':
            cursor = await db.execute('SELECT * FROM items WHERE category = ? ORDER BY subcategory, name', (category,))
        else:
            cursor = await db.execute('SELECT * FROM items ORDER BY category, subcategory, name')
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

COCKTAIL_ALIASES = {
    'cocktail_1': ['апероль', 'спритц', 'аперол'],
    'cocktail_2': ['сарти', 'сарти спритц', 'сарти роза'],
    'cocktail_3': ['кампари', 'кампари спритц'],
    'cocktail_set_1': ['сила трех', 'сет', 'аперитивный сет'],
    'cocktail_4': ['негрони'],
    'cocktail_5': ['кловер', 'кловер клаб', 'малина'],
    'cocktail_6': ['рамос', 'рамос физ', 'секрет м'],
    'cocktail_7': ['грассхоппер', 'кузнечик'],
    'cocktail_8': ['драй мартини', 'мартини'],
    'cocktail_9': ['эспрессо', 'эспрессо мартини', 'амаро тини'],
    'cocktail_10': ['папа док'],
    'cocktail_11': ['чинар', 'цинар', 'чинар кап', 'артишок'],
    'cocktail_12': ['сазерак', 'саз', 'саз-эйр-ак'],
    'cocktail_13': ['мари лаво', 'коктейль мари лаво'],
    'cocktail_14': ['харрикейн', 'ураган'],
    'cocktail_15': ['вуду', 'вуду фэшн', 'вуду фешн', 'олд фэшн'],
    'cocktail_16': ['ожен', 'абсент фраппе'],
    'cocktail_17': ['френч', 'брамбл', 'рояль'],
    'cocktail_18': ['беллини', 'лайлак', 'сирень'],
    'cocktail_19': ['порн стар', 'порнстар', 'маракуйя'],
    'cocktail_20': ['мохито', 'мохито лаво'],
    'cocktail_21': ['блади мэри', 'кровавая мэри', 'сангрита'],
    'cocktail_22': ['плам сауэр', 'сливовый сауэр', 'слива'],
    'cocktail_23': ['маргарита', 'розовая маргарита'],
    'cocktail_24': ['пеар пай', 'грушевый пирог', 'груша'],
    'cocktail_25': ['авиация', 'авиэйшн'],
    'cocktail_26': ['пенициллин', 'манго пенициллин'],
    'cocktail_27': ['гри гри', 'гри-гри', 'амулет'],
    'cocktail_28': ['зе витч квин', 'витч квин', 'ведьма', 'королева ведьм'],
    'cocktail_29': ['конго', 'плас дю конго', 'плейс дю конго', 'старая площадь'],
    'cocktail_30': ['митан', 'алтарь', 'столб'],
    'food_32': ['фиш', 'фиш энд потейто', 'треска', 'рыба']
}

def _norm_search(text: str) -> str:
    return (text or '').lower().replace('ё', 'е').strip()

async def search_items(query: str, category: str = None):
    all_items = await get_all_items(category)
    q = _norm_search(query)
    if not q:
        return all_items[:20]

    q_words = [w for w in q.split() if len(w) > 1]
    if not q_words:
        q_words = [q]

    scored = []
    for it in all_items:
        score = 0
        name = _norm_search(it['name'])
        comp = _norm_search(it.get('composition', ''))
        details = _norm_search(it.get('details', ''))
        pitch = _norm_search(it.get('pitch_script', ''))
        allergens = _norm_search(it.get('allergens', ''))
        aliases = [_norm_search(a) for a in COCKTAIL_ALIASES.get(it['id'], [])]

        # 1. Exact or prefix match in item name
        if q == name:
            score += 150
        elif name.startswith(q):
            score += 100
        elif q in name:
            score += 80

        # 2. Match with phonetic / Russian aliases (e.g. митан -> Mitan)
        for alias in aliases:
            if q == alias:
                score += 130
            elif alias.startswith(q) or q in alias:
                score += 80

        # 3. Composition match
        if q in comp:
            score += 45

        # 4. Details / pitch
        if q in details:
            score += 20
        if q in pitch:
            score += 15

        # 5. Allergens
        if q in allergens:
            score += 25

        # 6. Word-level match
        for w in q_words:
            if w in name:
                score += 30
            for alias in aliases:
                if w in alias:
                    score += 25
            if w in comp:
                score += 15

        if score > 0:
            scored.append((score, it))

    # Sort by relevance score descending
    scored.sort(key=lambda x: x[0], reverse=True)
    return [it for _, it in scored[:20]]

async def get_next_training_item(user_id: int, category: str = 'all'):
    """
    Leitner Spaced Repetition selector:
    - Box 1 (Struggling/New): Weight 6
    - Box 2 (Learning): Weight 3
    - Box 3 (Mastered): Weight 1
    If category is 'mistakes', returns items where mistake_count > 0 and box < 3.
    """
    async with get_connection() as db:
        db.row_factory = aiosqlite.Row
        if category == 'mistakes':
            cursor = await db.execute('''
                SELECT i.*, COALESCE(up.box, 1) as box, COALESCE(up.mistake_count, 0) as mistake_count
                FROM items i
                JOIN user_progress up ON i.id = up.item_id AND up.user_id = ?
                WHERE up.mistake_count > 0 AND up.box < 3
                ORDER BY up.mistake_count DESC, up.last_reviewed ASC
            ''', (user_id,))
            rows = await cursor.fetchall()
            if not rows:
                return None
            items = [dict(r) for r in rows]
            return random.choice(items[:min(5, len(items))])

        query = '''
            SELECT i.*, COALESCE(up.box, 1) as box, COALESCE(up.last_reviewed, '2000-01-01') as last_reviewed
            FROM items i
            LEFT JOIN user_progress up ON i.id = up.item_id AND up.user_id = ?
        '''
        params = [user_id]
        if category in ('cocktails', 'food'):
            query += ' WHERE i.category = ?'
            params.append(category)

        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        if not rows:
            return None

        items = [dict(r) for r in rows]
        weights = []
        for it in items:
            box = it.get('box', 1)
            if box == 1:
                weights.append(6)
            elif box == 2:
                weights.append(3)
            else:
                weights.append(1)

        selected = random.choices(items, weights=weights, k=1)[0]
        return selected

async def record_answer(user_id: int, item_id: str, grade: str):
    """
    grade: 'known' (🟢), 'partial' (🟡), 'unknown' (🔴)
    """
    async with get_connection() as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('''
            SELECT box, known_count, mistake_count FROM user_progress
            WHERE user_id = ? AND item_id = ?
        ''', (user_id, item_id))
        row = await cursor.fetchone()

        if not row:
            box = 1
            known_cnt = 0
            mistake_cnt = 0
        else:
            box = row['box']
            known_cnt = row['known_count']
            mistake_cnt = row['mistake_count']

        if grade == 'known':
            box = min(3, box + 1)
            known_cnt += 1
        elif grade == 'partial':
            box = min(2, max(1, box))
        elif grade == 'unknown':
            box = 1
            mistake_cnt += 1

        await db.execute('''
            INSERT INTO user_progress (user_id, item_id, box, known_count, mistake_count, last_reviewed)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id, item_id) DO UPDATE SET
                box = excluded.box,
                known_count = excluded.known_count,
                mistake_count = excluded.mistake_count,
                last_reviewed = CURRENT_TIMESTAMP
        ''', (user_id, item_id, box, known_cnt, mistake_cnt))

        await db.commit()

async def get_user_stats(user_id: int):
    async with get_connection() as db:
        db.row_factory = aiosqlite.Row
        c_items = await db.execute('SELECT COUNT(*) FROM items')
        total_items = (await c_items.fetchone())[0]

        c_cocktails = await db.execute("SELECT COUNT(*) FROM items WHERE category = 'cocktails'")
        total_cocktails = (await c_cocktails.fetchone())[0]

        c_food = await db.execute("SELECT COUNT(*) FROM items WHERE category = 'food'")
        total_food = (await c_food.fetchone())[0]

        c_prog = await db.execute('''
            SELECT 
                COUNT(*) as studied,
                SUM(CASE WHEN box = 3 THEN 1 ELSE 0 END) as mastered,
                SUM(CASE WHEN box = 2 THEN 1 ELSE 0 END) as learning,
                SUM(CASE WHEN box = 1 THEN 1 ELSE 0 END) as struggling,
                SUM(known_count) as total_known,
                SUM(mistake_count) as total_mistakes
            FROM user_progress
            WHERE user_id = ?
        ''', (user_id,))
        prog = dict(await c_prog.fetchone())

        c_cocktail_prog = await db.execute('''
            SELECT 
                COUNT(*) as studied,
                SUM(CASE WHEN up.box = 3 THEN 1 ELSE 0 END) as mastered
            FROM user_progress up
            JOIN items i ON up.item_id = i.id
            WHERE up.user_id = ? AND i.category = 'cocktails'
        ''', (user_id,))
        cocktail_prog = dict(await c_cocktail_prog.fetchone())

        c_food_prog = await db.execute('''
            SELECT 
                COUNT(*) as studied,
                SUM(CASE WHEN up.box = 3 THEN 1 ELSE 0 END) as mastered
            FROM user_progress up
            JOIN items i ON up.item_id = i.id
            WHERE up.user_id = ? AND i.category = 'food'
        ''', (user_id,))
        food_prog = dict(await c_food_prog.fetchone())

        c_exams = await db.execute('''
            SELECT COUNT(*) as count, MAX(percentage) as best_score, AVG(percentage) as avg_score
            FROM exam_results WHERE user_id = ?
        ''', (user_id,))
        exams = dict(await c_exams.fetchone())

        return {
            'total_items': total_items,
            'total_cocktails': total_cocktails,
            'total_food': total_food,
            'studied': prog.get('studied') or 0,
            'mastered': prog.get('mastered') or 0,
            'learning': prog.get('learning') or 0,
            'struggling': prog.get('struggling') or 0,
            'total_known': prog.get('total_known') or 0,
            'total_mistakes': prog.get('total_mistakes') or 0,
            'cocktails_studied': cocktail_prog.get('studied') or 0,
            'cocktails_mastered': cocktail_prog.get('mastered') or 0,
            'food_studied': food_prog.get('studied') or 0,
            'food_mastered': food_prog.get('mastered') or 0,
            'exams_count': exams.get('count') or 0,
            'best_exam_score': exams.get('best_score'),
            'avg_exam_score': exams.get('avg_score')
        }

async def save_exam_result(user_id: int, category: str, score: int, total: int):
    pct = round((score / total) * 100, 1) if total > 0 else 0
    async with get_connection() as db:
        db.row_factory = aiosqlite.Row
        await db.execute('''
            INSERT INTO exam_results (user_id, category, score, total, percentage)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, category, score, total, pct))
        await db.commit()
    return pct

async def get_manager_analytics():
    async with get_connection() as db:
        db.row_factory = aiosqlite.Row
        c_users = await db.execute('SELECT COUNT(*) FROM users')
        users_count = (await c_users.fetchone())[0]

        c_top_cocktails = await db.execute('''
            SELECT i.name, SUM(up.mistake_count) as mistakes
            FROM user_progress up
            JOIN items i ON up.item_id = i.id
            WHERE i.category = 'cocktails' AND up.mistake_count > 0
            GROUP BY i.id
            ORDER BY mistakes DESC
            LIMIT 5
        ''')
        top_cocktails = [dict(r) for r in await c_top_cocktails.fetchall()]

        c_top_food = await db.execute('''
            SELECT i.name, SUM(up.mistake_count) as mistakes
            FROM user_progress up
            JOIN items i ON up.item_id = i.id
            WHERE i.category = 'food' AND up.mistake_count > 0
            GROUP BY i.id
            ORDER BY mistakes DESC
            LIMIT 5
        ''')
        top_food = [dict(r) for r in await c_top_food.fetchall()]

        c_recent_exams = await db.execute('''
            SELECT e.*, u.full_name, u.username
            FROM exam_results e
            JOIN users u ON e.user_id = u.user_id
            ORDER BY e.created_at DESC
            LIMIT 10
        ''')
        recent_exams = [dict(r) for r in await c_recent_exams.fetchall()]

        return {
            'users_count': users_count,
            'top_cocktails': top_cocktails,
            'top_food': top_food,
            'recent_exams': recent_exams
        }


async def create_assigned_exam(user_id: int, category: str, assigned_by: int, ticket_count: int = 5):
    all_items = await get_all_items(category=category if category in ('cocktails', 'food') else None)
    if not all_items:
        return None
    sample_size = min(ticket_count, len(all_items))
    selected = random.sample(all_items, sample_size)
    item_ids = [it['id'] for it in selected]

    async with get_connection() as db:
        db.row_factory = aiosqlite.Row
        # Cancel any previous pending assigned exam
        await db.execute('''
            UPDATE assigned_exams SET status = 'cancelled'
            WHERE user_id = ? AND status IN ('pending', 'in_progress')
        ''', (user_id,))

        cursor = await db.execute('''
            INSERT INTO assigned_exams (user_id, category, assigned_by, ticket_count, items_json, status, total)
            VALUES (?, ?, ?, ?, ?, 'pending', ?)
        ''', (user_id, category, assigned_by, sample_size, json.dumps(item_ids), sample_size))
        await db.commit()
        exam_id = cursor.lastrowid

        cursor = await db.execute('SELECT * FROM assigned_exams WHERE id = ?', (exam_id,))
        row = await cursor.fetchone()
        return dict(row)

async def get_pending_assigned_exam(user_id: int):
    async with get_connection() as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('''
            SELECT * FROM assigned_exams
            WHERE user_id = ? AND status IN ('pending', 'in_progress')
            ORDER BY created_at DESC LIMIT 1
        ''', (user_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def get_assigned_exam(exam_id: int):
    async with get_connection() as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('SELECT * FROM assigned_exams WHERE id = ?', (exam_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def update_assigned_exam_status(exam_id: int, status: str):
    async with get_connection() as db:
        await db.execute('UPDATE assigned_exams SET status = ? WHERE id = ?', (status, exam_id))
        await db.commit()

async def save_voice_submission(assigned_exam_id: int, item_id: str, ticket_num: int, voice_file_id: str):
    async with get_connection() as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('''
            INSERT INTO voice_submissions (assigned_exam_id, item_id, ticket_num, voice_file_id)
            VALUES (?, ?, ?, ?)
        ''', (assigned_exam_id, item_id, ticket_num, voice_file_id))
        await db.commit()
        return cursor.lastrowid

async def get_voice_submissions(assigned_exam_id: int):
    async with get_connection() as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('''
            SELECT vs.*, i.name as item_name, i.category as item_category, 
                   i.composition as item_composition, i.details as item_details,
                   i.pitch_script as item_pitch_script, i.allergens as item_allergens
            FROM voice_submissions vs
            JOIN items i ON vs.item_id = i.id
            WHERE vs.assigned_exam_id = ?
            ORDER BY vs.ticket_num ASC
        ''', (assigned_exam_id,))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

async def grade_voice_submission(submission_id: int, grade: int, graded_by: int):
    async with get_connection() as db:
        db.row_factory = aiosqlite.Row
        await db.execute('''
            UPDATE voice_submissions 
            SET grade = ?, graded_by = ?
            WHERE id = ?
        ''', (grade, graded_by, submission_id))
        await db.commit()

        cursor = await db.execute('SELECT * FROM voice_submissions WHERE id = ?', (submission_id,))
        sub = await cursor.fetchone()
        return dict(sub) if sub else None

async def check_exam_grading_completed(assigned_exam_id: int):
    """
    Checks if all tickets in the exam have been graded.
    If so, updates assigned_exams with final score and graded status.
    Returns (is_completed: bool, score: int, total: int, percentage: float)
    """
    async with get_connection() as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('''
            SELECT * FROM voice_submissions WHERE assigned_exam_id = ?
        ''', (assigned_exam_id,))
        rows = await cursor.fetchall()
        if not rows:
            return False, 0, 0, 0.0

        total = len(rows)
        graded_count = sum(1 for r in rows if r['grade'] is not None)
        if graded_count < total:
            return False, 0, total, 0.0

        score = sum(1 for r in rows if r['grade'] == 1)
        pct = round((score / total) * 100, 1)

        await db.execute('''
            UPDATE assigned_exams
            SET status = 'graded', score = ?, graded_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (score, assigned_exam_id))

        # Also insert into exam_results for general stats
        cursor_exam = await db.execute('SELECT * FROM assigned_exams WHERE id = ?', (assigned_exam_id,))
        exam = await cursor_exam.fetchone()
        if exam:
            await db.execute('''
                INSERT INTO exam_results (user_id, category, score, total, percentage)
                VALUES (?, ?, ?, ?, ?)
            ''', (exam['user_id'], f"voice_{exam['category']}", score, total, pct))

        await db.commit()
        return True, score, total, pct


async def set_user_role(user_id: int, role: str):
    async with get_connection() as db:
        await db.execute('UPDATE users SET role = ? WHERE user_id = ?', (role, user_id))
        await db.commit()
