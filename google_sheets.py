import gspread
from google.oauth2.service_account import Credentials

from config import get_env, get_google_service_account_info

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
]


def get_worksheet():
    credentials = Credentials.from_service_account_info(
        get_google_service_account_info(),
        scopes=SCOPES,
    )
    client = gspread.authorize(credentials)
    spreadsheet = client.open_by_key(get_env("GOOGLE_SHEETS_SPREADSHEET_ID"))
    worksheet_name = get_env("GOOGLE_SHEETS_WORKSHEET_NAME")
    return spreadsheet.worksheet(worksheet_name)


def ensure_sheet_header():
    worksheet = get_worksheet()
    if not worksheet.row_values(1):
        worksheet.append_row(
            [
                "timestamp",
                "date",
                "month",
                "amount",
                "direction",
                "category",
                "notes",
                "raw_message",
                "sms_sender",
                "source",
            ]
        )


def append_transaction_to_sheet(transaction):
    ensure_sheet_header()
    worksheet = get_worksheet()
    worksheet.append_row(
        [
            transaction.get("timestamp", ""),
            transaction.get("date", ""),
            transaction.get("month", ""),
            transaction.get("amount", ""),
            transaction.get("direction", ""),
            transaction.get("category", ""),
            transaction.get("notes", ""),
            transaction.get("raw_message", ""),
            transaction.get("sms_sender", ""),
            transaction.get("source", ""),
        ]
    )
