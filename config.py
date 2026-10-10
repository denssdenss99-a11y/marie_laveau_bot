import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN', '')
if not BOT_TOKEN:
    # Fallback to local .env if present
    BOT_TOKEN = os.getenv('BOT_TOKEN', '')

# Admin Telegram IDs (comma-separated in .env)
admin_ids_raw = os.getenv('ADMIN_IDS', '1368643174')
ADMIN_IDS = [int(i.strip()) for i in admin_ids_raw.split(',') if i.strip().isdigit()]
if not ADMIN_IDS:
    ADMIN_IDS = [1368643174]

ITEMS_PER_PAGE = 6
EXAM_QUESTIONS_COUNT = 15
