import os

from dotenv import load_dotenv

load_dotenv()

TOKEN = os.environ["TOKEN"]
DB_URI = os.environ["DB_URI"]
DEBUG = os.environ.get("DEBUG") == "TRUE"
SPREADSHEET_ID = os.environ["SPREADSHEET_ID"]
FROM_CHAT_ID = int(os.environ["FROM_CHAT_ID"])
API_ID = os.environ["API_ID"]
API_HASH = os.environ["API_HASH"]
SESSION_NAME = "real_estate_rent_bot"
SENTRY_DSN = os.environ["SENTRY_DSN"]
STATIC_FROM_CHAT_ID = int(os.environ["STATIC_FROM_CHAT_ID"])
WELCOME_VIDEO = os.environ["WELCOME_VIDEO"]
