import os

from dotenv import load_dotenv

load_dotenv()

TOKEN = os.environ["TOKEN"]
DEBUG = os.environ.get("DEBUG") == "TRUE"
SPREADSHEET_URL = os.environ["SPREADSHEET_URL"]