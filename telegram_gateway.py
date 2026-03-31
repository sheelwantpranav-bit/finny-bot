import httpx

from config import get_env


def get_bot_api_base():
    token = get_env("TELEGRAM_TOKEN")
    return f"https://api.telegram.org/bot{token}"


async def send_telegram_message(chat_id, text):
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(
            f"{get_bot_api_base()}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text,
            },
        )
        response.raise_for_status()
        return response.json()


async def set_telegram_webhook(webhook_url):
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(
            f"{get_bot_api_base()}/setWebhook",
            json={"url": webhook_url},
        )
        response.raise_for_status()
        return response.json()
