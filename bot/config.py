import os

from dotenv import load_dotenv

load_dotenv()

TOKEN = os.environ["TOKEN"]
DB_URI = os.environ["DB_URI"]
DEBUG = os.environ.get("DEBUG") == "TRUE"
FROM_CHAT_ID = int(os.environ["FROM_CHAT_ID"])
API_ID = os.environ["API_ID"]
API_HASH = os.environ["API_HASH"]
SESSION_NAME = "real_estate_rent_bot"
SENTRY_DSN = os.environ["SENTRY_DSN"]
# SENTRY_ENV = os.environ["SENTRY_ENV"]

STATIC_FROM_CHAT_ID = int(os.environ["STATIC_FROM_CHAT_ID"])
WELCOME_VIDEO = os.environ["WELCOME_VIDEO"]

ADS_SHEET_ID = os.environ["ADS_SHEET_ID"]
ADS_SPREADSHEET_ID = os.environ["ADS_SPREADSHEET_ID"]
ADS_SHEET_NAME = os.environ["ADS_SHEET_NAME"]
RENT_SPREADSHEET_ID = os.environ["RENT_SPREADSHEET_ID"]
