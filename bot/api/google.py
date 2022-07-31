from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
from bot import config

SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']


class GoogleApi:
    creds = None

    def __init__(self, base_path: Optional[Path] = None):
        if base_path is None:
            base_path = Path() / 'credentials'
        self.token_path = base_path / 'token.json'
        self.client_secret_path = base_path / 'client_secret.json'
        if self.token_path.exists():
            self.creds = Credentials.from_authorized_user_file(self.token_path.as_posix(), SCOPES)
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            self.service = build('sheets', 'v4', credentials=self.creds)

    def generate_creds(self):
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        # If there are no (valid) credentials available, let the user log in.
        if not self.creds or not self.creds.valid:
            flow = InstalledAppFlow.from_client_secrets_file(self.client_secret_path.as_posix(), SCOPES)
            self.creds = flow.run_local_server(port=57664)
            # Save the credentials for the next run
            self.token_path.write_text(self.creds.to_json())

    def get_sheet_data(self, sheet_name, ):
        range_name = f'{sheet_name}!A1:AD'
        # Call the Sheets API
        sheet = self.service.spreadsheets()
        result = sheet.values().get(spreadsheetId=config.SPREADSHEET_ID,
                                    range=range_name).execute()
        values = result.get('values', [])

        return values
