from __future__ import annotations

from typing import Any

DRIVE_READONLY_SCOPE = "https://www.googleapis.com/auth/drive.readonly"
SHEETS_READONLY_SCOPE = "https://www.googleapis.com/auth/spreadsheets.readonly"


class DriveClient:
    def __init__(self, service_account_info: dict[str, Any]):
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        credentials = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=[DRIVE_READONLY_SCOPE, SHEETS_READONLY_SCOPE],
        )
        self._sheets = build("sheets", "v4", credentials=credentials, cache_discovery=False)

    def read_sheet_values(self, spreadsheet_id: str, sheet_name: str, range_a1: str = "A1:AO1000") -> list[list[Any]]:
        escaped = sheet_name.replace("'", "''")
        a1 = f"'{escaped}'!{range_a1}"
        response = (
            self._sheets.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=a1, valueRenderOption="UNFORMATTED_VALUE")
            .execute()
        )
        return response.get("values", [])
