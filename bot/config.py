import os

from dotenv import load_dotenv

load_dotenv()

TOKEN = os.environ["TOKEN"]
DB_URI = os.environ["DB_URI"]
DEBUG = os.environ.get("DEBUG") == "TRUE"
SPREADSHEET_ID = os.environ["SPREADSHEET_ID"]
