import os
import time
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()

from pyrogram import Client
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiohttp import web

from config import Config
from route import web_server


class Bot(Client):
    def __init__(self):
        # Ensure the session/database directory exists before Pyrogram opens its file session.
        os.makedirs(Config.STORAGE_DIR, exist_ok=True)
        os.makedirs(Config.TEMP_DIR, exist_ok=True)
        Config.validate()
        super().__init__(
            name="auto_rename_bot",
            api_id=int(Config.API_ID) if Config.API_ID else None,
            api_hash=Config.API_HASH or None,
            bot_token=Config.BOT_TOKEN,
            workers=100,
            plugins={"root": "plugins"},
            sleep_threshold=30,
            max_concurrent_transmissions=Config.MAX_CONCURRENT_TRANSMISSIONS,
            workdir=Config.STORAGE_DIR,
        )
        self.start_time = time.time()

    async def start(self, *args, **kwargs):
        await super().start(*args, **kwargs)
        me = await self.get_me()
        self.mention = me.mention
        self.username = me.username
        self.uptime = self.start_time

        if Config.WEBHOOK:
            app = web.AppRunner(await web_server())
            await app.setup()
            await web.TCPSite(app, "0.0.0.0", Config.PORT).start()

        os.makedirs(Config.STORAGE_DIR, exist_ok=True)
        print(f"{me.first_name} started successfully.")

        if Config.LOG_CHANNEL is not None:
            uptime = str(timedelta(seconds=int(time.time() - self.start_time)))
            try:
                await self.send_message(
                    Config.LOG_CHANNEL,
                    f"**✅ Bot started**\n\n**Uptime:** `{uptime}`\n**Bot:** {me.mention}",
                    reply_markup=InlineKeyboardMarkup(
                        [[InlineKeyboardButton("Updates", url="https://t.me/codeflix_bots")]]
                    ),
                )
            except Exception as error:
                print(f"Startup log could not be sent: {error}")


if __name__ == "__main__":
    Bot().run()
