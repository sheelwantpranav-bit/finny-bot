# Finny Setup Guide

This project now supports the full webhook flow:

1. MacroDroid sends bank SMS to your FastAPI server.
2. FastAPI parses the SMS and creates a pending transaction.
3. Finny sends you a Telegram question.
4. Your Telegram reply is saved to local JSON and Google Sheets.

## 1. Environment variables

Set these in Railway:

- `PORT`
- `APP_BASE_URL`
- `FINNY_WEBHOOK_SECRET`
- `TELEGRAM_TOKEN`
- `TELEGRAM_USER_ID`
- `GROQ_API_KEY`
- `GOOGLE_SHEETS_SPREADSHEET_ID`
- `GOOGLE_SHEETS_WORKSHEET_NAME`
- `GOOGLE_SERVICE_ACCOUNT_JSON`

What each one means:

- `APP_BASE_URL`: your Railway public URL, for example `https://your-app.up.railway.app`
- `FINNY_WEBHOOK_SECRET`: shared secret used by MacroDroid and the webhook setup route
- `TELEGRAM_TOKEN`: your bot token from BotFather
- `TELEGRAM_USER_ID`: only this Telegram account can talk to the bot
- `GOOGLE_SERVICE_ACCOUNT_JSON`: the full service account JSON copied into one environment variable

## 2. Start the app

Railway start command:

```bash
python telegram_bot.py
```

That launches `uvicorn` and serves the FastAPI app from `finny_api.py`.

## 3. Health check

Open:

```text
GET /health
```

You should see a healthy JSON response.

## 4. Set Telegram webhook

After deploy, call:

```text
POST /setup/telegram-webhook
Header: X-Finny-Secret: <your secret>
```

This tells Telegram to send all bot messages to:

```text
/webhooks/telegram
```

## 5. Configure MacroDroid

Create a MacroDroid flow:

- Trigger: incoming SMS
- Filter: your bank senders
- Action: HTTP Request

Request details:

- Method: `POST`
- URL: `https://your-app.up.railway.app/webhooks/macrodroid-sms`
- Header: `X-Finny-Secret: your-secret`
- Body type: JSON

JSON body:

```json
{
  "message": "[sms_body]",
  "sender": "[sms_sender]",
  "received_at": "[timestamp]"
}
```

## 6. Google Sheets setup

Before testing, create a worksheet and share the spreadsheet with the service account email.

Expected columns:

- `timestamp`
- `date`
- `month`
- `amount`
- `direction`
- `category`
- `notes`
- `raw_message`
- `sms_sender`
- `source`

## 7. Real test

Once everything is wired:

1. A bank SMS arrives on your phone.
2. MacroDroid sends it to Finny.
3. Finny sends you a Telegram question.
4. You reply with the category.
5. Finny saves it locally and appends one row to Google Sheets.
