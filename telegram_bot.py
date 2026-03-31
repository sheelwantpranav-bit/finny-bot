# telegram_bot.py
# Compatibility launcher for the new webhook-based Finny app.

import os

import uvicorn


def main():
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("finny_api:app", host="0.0.0.0", port=port, reload=False)


if __name__ == "__main__":
    main()
