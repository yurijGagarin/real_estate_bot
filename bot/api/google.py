import os.path
from pathlib import Path
from typing import Optional, List

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from loguru import logger

from bot import config
# If modifying these scopes, delete the file token.json.
from bot.config import ADS_SHEET_NAME, ADS_SPREADSHEET_ID, ADS_SHEET_ID

SCOPES = ["https://www.googleapis.com/auth/drive",
          "https://www.googleapis.com/auth/spreadsheets",
          ]


class GoogleApi:
    creds = None

    def __init__(self, base_path: Optional[Path] = None):
        if base_path is None:
            base_path = Path() / "credentials"
        self.token_path = base_path / "token.json"
        self.client_secret_path = base_path / "client_secret.json"
        if self.token_path.exists():
            self.creds = Credentials.from_authorized_user_file(
                self.token_path.as_posix(), SCOPES
            )
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            self.drive_service = build('drive', 'v3', credentials=self.creds)
            self.sheet_service = build("sheets", "v4", credentials=self.creds)
        else:
            raise Exception(f'No token: "{self.token_path.as_posix()}"')

    def generate_creds(self):
        """
        The file token.json stores the user's access and refresh tokens, and is
        created automatically when the authorization flow completes for the first
        time.
        If there are no (valid) credentials available, let the user log in.
        """
        if not self.creds or not self.creds.valid:
            flow = InstalledAppFlow.from_client_secrets_file(
                self.client_secret_path.as_posix(), SCOPES
            )
            self.creds = flow.run_local_server(port=8080)
            # Save the credentials for the next run
            self.token_path.write_text(self.creds.to_json())

    def get_folder_by_name(self, folder_name: int | str, parent_folder=None):
        """
        Checks if folder already exist
        :param folder_name: user tg id
        :return: Folder or None
        """
        q = f'name="{folder_name}"'

        if parent_folder is not None:
            parent_folder = self.get_folder_by_name(folder_name=parent_folder)
            if parent_folder is None:
                return None
            parent_folder_id = parent_folder.get('id')
            q += f" and '{parent_folder_id}' in parents"

        search_result = self.drive_service.files().list(q=q).execute()
        files = search_result.get('files')
        if len(files) > 0:
            return files[0]
        return None

    async def create_folder(self, folder_name: str, parent_folder: str | None = None):
        """
        Creates Folder
        :param parent_folder:
        :param folder_name: user tg id
        :return: Folder
        """
        try:
            folder = self.get_folder_by_name(folder_name, parent_folder=parent_folder)
            if not folder:
                parent_folder_ids = []
                if parent_folder is not None:
                    pf = await self.create_folder(parent_folder)
                    parent_folder_ids.append(pf.get('id'))

                file_metadata = {
                    'name': folder_name,
                    'parents': parent_folder_ids,
                    'mimeType': 'application/vnd.google-apps.folder'
                }
                folder = self.drive_service.files().create(body=file_metadata, fields='id'
                                                           ).execute()
                logger.info(f'Folder has created with ID: "{folder.get("id")}".')
        except HttpError as error:
            logger.error(f'An error occurred: {error}')
            raise error

        return folder

    async def upload_files_to_gdrive(self, subfolder_name: str, folder_name: str, folder_from_upload):
        try:
            folder_to_upload = await self.create_folder(folder_name=subfolder_name, parent_folder=folder_name)
            folder_to_upload_id = folder_to_upload.get('id')
            if len(folder_from_upload) > 0:
                for file_path in folder_from_upload:
                    file_name = os.path.basename(file_path)
                    file_metadata = {
                        'name': file_name,
                        'parents': [folder_to_upload_id],
                    }
                    media = MediaFileUpload(file_path)
                    upload = self.drive_service.files().create(
                        body=file_metadata,
                        media_body=media,
                        fields='id'
                    ).execute()
                    logger.info(f'File has been upload with ID: "{upload.get("id")}".')

        except HttpError as error:
            logger.error(f'An error occurred: {error}')
            raise error

        return folder_to_upload_id

    def insert_new_row_to_spreadsheet(self):
        try:
            sheet = self.sheet_service.spreadsheets()
            request_body = {
                'requests': [
                    {
                        'insertDimension': {
                            'range': {
                                "sheetId": ADS_SHEET_ID,
                                "dimension": "ROWS",
                                "startIndex": 1,
                                "endIndex": 2
                            }
                        }
                    }
                ]
            }
            sheet.batchUpdate(spreadsheetId=ADS_SPREADSHEET_ID,
                              body=request_body).execute()
        except HttpError as error:
            logger.error(f'An error occurred: {error}')
            raise error

    def update_values(self, values: List[List]):
        try:
            self.insert_new_row_to_spreadsheet()
            body = {
                'values': values
            }
            result = self.sheet_service.spreadsheets().values().update(
                spreadsheetId=ADS_SPREADSHEET_ID, range=f"{ADS_SHEET_NAME}!A2:Q2",
                valueInputOption='RAW', body=body).execute()
            return result
        except HttpError as error:
            print(f"An error occurred: {error}")
            raise error

    def get_sheet_data(
            self,
            sheet_name,
    ):
        range_name = f"{sheet_name}!A1:AD"
        # Call the Sheets API
        sheet = self.sheet_service.spreadsheets()
        result = (
            sheet.values()
            .get(spreadsheetId=config.RENT_SPREADSHEET_ID, range=range_name)
            .execute()
        )
        values = result.get("values", [])

        return values

    def batch_update_google_maps_link_by_row_idx(self, indexes: List[int], g_maps_link:str):
        try:
            batch_update_spreadsheet_request_body = {'requests': []}
            for idx in indexes:
                batch_update_spreadsheet_request_body['requests'].append(
                    self.create_spreadsheet_batchupdate_request_for_google_maps_column_by_row_idx(idx, g_maps_link))
            request = self.sheet_service.spreadsheets().batchUpdate(spreadsheetId=config.RENT_SPREADSHEET_ID,
                                                                    body=batch_update_spreadsheet_request_body)
            response = request.execute()
            return response

        except HttpError as error:
            print(f"An error occurred: {error}")
            return error

    @staticmethod
    def create_spreadsheet_batchupdate_request_for_google_maps_column_by_row_idx(idx: int, google_maps_link:str) -> dict:

        return {
            "updateCells":
                {
                    "rows": [{"values": [{"userEnteredValue": {"stringValue": google_maps_link}}]}],
                    "fields": '*',
                    "range": {
                        "sheetId": config.RENT_SHEET_ID,
                        "startRowIndex": idx - 1,
                        "endRowIndex": idx,
                        "startColumnIndex": 16,
                        "endColumnIndex": 17
                    }
                }

        }
