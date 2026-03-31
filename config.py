import json
import os


def get_env(name, default=None):
    value = os.environ.get(name, default)
    if value is None:
        raise RuntimeError(f"{name} is not set.")
    return value


def get_optional_env(name, default=''):
    return os.environ.get(name, default)


def get_telegram_user_id():
    return int(get_env("TELEGRAM_USER_ID"))


def get_google_service_account_info():
    raw_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if raw_json:
        return json.loads(raw_json)

    json_path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE", "").strip()
    if json_path:
        with open(json_path, 'r') as f:
            return json.load(f)

    raise RuntimeError(
        "Set GOOGLE_SERVICE_ACCOUNT_JSON or GOOGLE_SERVICE_ACCOUNT_FILE for Google Sheets access."
    )
