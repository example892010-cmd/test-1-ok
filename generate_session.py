"""Create a reusable Pyrogram bot session for deployments with only three env vars.

Run once with BOT_TOKEN, API_ID and API_HASH in a local .env file. Keep the
resulting storage/auto_rename_bot.session private and copy it to persistent
storage on the deployment server. API_ID/API_HASH can then be omitted at runtime.
"""
import os

from dotenv import load_dotenv
from pyrogram import Client

load_dotenv()

from config import Config  # noqa: E402


def main():
    if not Config.BOT_TOKEN:
        raise SystemExit("BOT_TOKEN is missing from the environment")
    if not Config.API_ID or not Config.API_HASH:
        raise SystemExit("For first-time session creation, set both API_ID and API_HASH")

    os.makedirs(Config.STORAGE_DIR, exist_ok=True)
    session_path = os.path.join(Config.STORAGE_DIR, "auto_rename_bot.session")
    if os.path.exists(session_path):
        raise SystemExit(f"Session already exists: {session_path} (not overwriting it)")

    client = Client(
        name="auto_rename_bot",
        api_id=int(Config.API_ID),
        api_hash=Config.API_HASH,
        bot_token=Config.BOT_TOKEN,
        workdir=Config.STORAGE_DIR,
    )
    started = False
    try:
        client.start()
        started = True
        me = client.get_me()
        print(f"Created Pyrogram session for @{me.username or me.id}")
    finally:
        if started:
            client.stop()
    print(f"Keep this file private and copy it to the deployment storage: {session_path}")


if __name__ == "__main__":
    main()
