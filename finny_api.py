import hashlib
from datetime import datetime

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from agent import (
    ask_about_transaction,
    extract_category_reply,
    generate_clarification_question,
    generate_save_confirmation,
    get_spending_summary_response,
)
from config import get_env, get_optional_env, get_telegram_user_id
from google_sheets import append_transaction_to_sheet
from parser import parse_bank_message
from storage import (
    create_pending_transaction,
    get_oldest_pending_transaction,
    has_seen_source_key,
    mark_pending_transaction_completed,
    save_transaction,
    update_pending_transaction,
)
from telegram_gateway import send_telegram_message, set_telegram_webhook

app = FastAPI(title="Finny Webhooks")


class MacroDroidSMSPayload(BaseModel):
    message: str
    sender: str | None = ""
    received_at: str | None = ""


def build_sms_dedupe_key(message, sender, received_at):
    raw_value = f"{message}|{sender}|{received_at}"
    return hashlib.sha256(raw_value.encode("utf-8")).hexdigest()


def ensure_secret(provided_secret):
    expected_secret = get_env("FINNY_WEBHOOK_SECRET")
    if provided_secret != expected_secret:
        raise HTTPException(status_code=401, detail="Invalid webhook secret.")


def ensure_telegram_user(telegram_user_id):
    if telegram_user_id != get_telegram_user_id():
        raise HTTPException(status_code=403, detail="Unauthorized Telegram user.")


def extract_message_info(update):
    message = update.get("message") or update.get("edited_message") or {}
    chat = message.get("chat") or {}
    user = message.get("from") or {}
    return {
        "text": (message.get("text") or "").strip(),
        "chat_id": chat.get("id"),
        "telegram_user_id": user.get("id"),
    }


def build_transaction_payload(pending, category, notes):
    now = datetime.now()
    return {
        "timestamp": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "month": now.strftime("%Y-%m"),
        "amount": pending["amount"],
        "direction": pending["direction"],
        "category": category.lower().strip(),
        "notes": notes,
        "raw_message": pending.get("raw_message", ""),
        "sms_sender": pending.get("sender", ""),
        "source": "telegram+macrodroid",
    }


@app.get("/health")
async def health():
    return {
        "ok": True,
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.post("/setup/telegram-webhook")
async def setup_telegram_webhook(x_finny_secret: str = Header(default="")):
    ensure_secret(x_finny_secret)
    app_base_url = get_env("APP_BASE_URL").rstrip("/")
    result = await set_telegram_webhook(f"{app_base_url}/webhooks/telegram")
    return {
        "ok": True,
        "telegram_result": result,
    }


@app.post("/webhooks/macrodroid-sms")
async def macrodroid_sms_webhook(
    payload: MacroDroidSMSPayload,
    x_finny_secret: str = Header(default=""),
):
    ensure_secret(x_finny_secret)

    authorized_user_id = get_telegram_user_id()
    dedupe_key = build_sms_dedupe_key(
        payload.message.strip(),
        payload.sender or "",
        payload.received_at or "",
    )

    if has_seen_source_key(dedupe_key):
        return {
            "ok": True,
            "parse_success": False,
            "duplicate": True,
            "message": "This SMS was already received earlier.",
        }

    parsed = parse_bank_message(payload.message)
    if not parsed["parse_success"]:
        await send_telegram_message(
            authorized_user_id,
            "I saw a new SMS, but I couldn't read it as a bank transaction. Please check it once.",
        )
        return {
            "ok": True,
            "parse_success": False,
            "duplicate": False,
        }

    pending = create_pending_transaction(
        telegram_user_id=authorized_user_id,
        amount=parsed["amount"],
        direction=parsed["direction"],
        raw_message=payload.message,
        sender=payload.sender or "",
        received_at=payload.received_at or "",
        dedupe_key=dedupe_key,
    )
    question = ask_about_transaction(parsed["amount"], parsed["direction"], [])
    update_pending_transaction(pending["id"], last_question=question)
    await send_telegram_message(authorized_user_id, question)

    return {
        "ok": True,
        "parse_success": True,
        "pending_id": pending["id"],
        "amount": parsed["amount"],
        "direction": parsed["direction"],
    }


@app.post("/webhooks/telegram")
async def telegram_webhook(update: dict):
    message_info = extract_message_info(update)
    telegram_user_id = message_info["telegram_user_id"]
    chat_id = message_info["chat_id"]
    text = message_info["text"]

    if not telegram_user_id or not chat_id or not text:
        return {"ok": True, "ignored": True}

    ensure_telegram_user(telegram_user_id)

    if text == "/start":
        await send_telegram_message(
            chat_id,
            "Hey! I'm Finny.\nSend me bank transactions automatically from MacroDroid and I'll ask what you spent the money on.",
        )
        return {"ok": True, "handled": "start"}

    if text == "/summary":
        current_month = datetime.now().strftime("%Y-%m")
        summary = get_spending_summary_response(month=current_month)
        await send_telegram_message(chat_id, summary)
        return {"ok": True, "handled": "summary"}

    pending = get_oldest_pending_transaction(telegram_user_id)
    if not pending:
        await send_telegram_message(
            chat_id,
            "I don't have a pending transaction right now. Send /summary or wait for the next bank SMS.",
        )
        return {"ok": True, "handled": "no_pending"}

    extracted = extract_category_reply(
        pending["amount"],
        pending["direction"],
        text,
    )

    if not extracted["save"]:
        followup = generate_clarification_question(pending["amount"], text)
        update_pending_transaction(
            pending["id"],
            followup_count=pending.get("followup_count", 0) + 1,
            last_question=followup,
            last_reply=text,
        )
        await send_telegram_message(chat_id, followup)
        return {"ok": True, "handled": "clarification"}

    category = extracted["category"]

    transaction_payload = build_transaction_payload(pending, category, text)

    try:
        append_transaction_to_sheet(transaction_payload)
    except Exception as exc:
        update_pending_transaction(
            pending["id"],
            last_error=str(exc),
            last_reply=text,
        )
        raise HTTPException(
            status_code=500,
            detail="Google Sheets append failed, so the transaction is still pending.",
        ) from exc

    save_transaction(
        pending["amount"],
        pending["direction"],
        category,
        notes=text,
        source="telegram+macrodroid",
        raw_message=pending.get("raw_message", ""),
        sms_sender=pending.get("sender", ""),
        source_key=pending["id"],
    )

    mark_pending_transaction_completed(
        pending["id"],
        category=category,
        notes=text,
    )

    confirmation = generate_save_confirmation(
        pending["amount"],
        pending["direction"],
        category,
    )
    await send_telegram_message(chat_id, confirmation)

    return {
        "ok": True,
        "handled": "saved",
        "category": category,
    }


@app.get("/")
async def root():
    return {
        "ok": True,
        "message": "Finny is running.",
        "app_base_url": get_optional_env("APP_BASE_URL", ""),
    }
