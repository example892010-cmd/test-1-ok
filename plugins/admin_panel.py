from config import Config, Txt
from helper.database import codeflixbots
from pyrogram.types import Message
from pyrogram import Client, filters
from pyrogram.errors import FloodWait, InputUserDeactivated, UserIsBlocked, PeerIdInvalid
import os, sys, time, asyncio, logging, datetime
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
ADMIN_USER_ID = Config.ADMIN

# Flag to indicate if the bot is restarting
is_restarting = False

@Client.on_message(filters.command("restart") & filters.user(ADMIN_USER_ID))
async def restart_bot(b, m):
    global is_restarting
    if not is_restarting:
        is_restarting = True
        await m.reply_text("**Restarting.....**")

        # Gracefully stop the bot's event loop
        await b.stop()
        await asyncio.sleep(1)

        # Restart the bot process
        os.execl(sys.executable, sys.executable, *sys.argv)


@Client.on_message(filters.command("tutorial"))
async def tutorial(bot: Client, message: Message):
    user_id = message.from_user.id if message.from_user else message.chat.id
    format_template = await codeflixbots.get_format_template(user_id)
    await message.reply_text(
        text=Txt.FILE_NAME_TXT + (f"\n\n**Saved format:** `{format_template}`" if format_template else ""),
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("• ᴏᴡɴᴇʀ", url="https://t.me/cosmic_freak"),
             InlineKeyboardButton("• ᴛᴜᴛᴏʀɪᴀʟ", url="https://t.me/codeflix_bots")]
        ])
    )


@Client.on_message(filters.command(["stats", "status"]) & filters.user(Config.ADMIN))
async def get_stats(bot, message):
    total_users = await codeflixbots.total_users_count()
    uptime = time.strftime("%Hh%Mm%Ss", time.gmtime(time.time() - bot.uptime))    
    start_t = time.time()
    st = await message.reply('**Accessing The Details.....**')    
    end_t = time.time()
    time_taken_s = (end_t - start_t) * 1000
    await st.edit(text=f"**--Bot Status--** \n\n**⌚️ Bot Uptime :** {uptime} \n**🐌 Current Ping :** `{time_taken_s:.3f} ms` \n**👭 Total Users :** `{total_users}`")

@Client.on_message(filters.command("broadcast") & filters.user(Config.ADMIN) & filters.reply)
async def broadcast_handler(bot: Client, m: Message):
    if Config.LOG_CHANNEL is not None:
        try:
            user_mention = m.from_user.mention if m.from_user else "Admin"
            user_id = m.from_user.id if m.from_user else m.chat.id
            await bot.send_message(Config.LOG_CHANNEL, f"{user_mention} or {user_id} started the broadcast.")
        except Exception:
            logger.warning("Broadcast start log could not be sent", exc_info=True)
    all_users = await codeflixbots.get_all_users()
    broadcast_msg = m.reply_to_message
    sts_msg = await m.reply_text("Broadcast Started..!") 
    done = 0
    failed = 0
    success = 0
    start_time = time.time()
    total_users = await codeflixbots.total_users_count()
    for user in all_users:
        sts = await send_msg(user['_id'], broadcast_msg)
        if sts == 200:
           success += 1
        else:
           failed += 1
        if sts == 400:
           await codeflixbots.delete_user(user['_id'])
        done += 1
        if not done % 20:
           await sts_msg.edit(f"Broadcast In Progress: \n\nTotal Users {total_users} \nCompleted : {done} / {total_users}\nSuccess : {success}\nFailed : {failed}")
    completed_in = datetime.timedelta(seconds=int(time.time() - start_time))
    await sts_msg.edit(f"Bʀᴏᴀᴅᴄᴀꜱᴛ Cᴏᴍᴩʟᴇᴛᴇᴅ: \nCᴏᴍᴩʟᴇᴛᴇᴅ Iɴ `{completed_in}`.\n\nTotal Users {total_users}\nCompleted: {done} / {total_users}\nSuccess: {success}\nFailed: {failed}")
           
async def send_msg(user_id, message):
    try:
        await message.copy(chat_id=int(user_id))
        return 200
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await send_msg(user_id, message)
    except InputUserDeactivated:
        logger.info(f"{user_id} : Deactivated")
        return 400
    except UserIsBlocked:
        logger.info(f"{user_id} : Blocked The Bot")
        return 400
    except PeerIdInvalid:
        logger.info(f"{user_id} : User ID Invalid")
        return 400
    except Exception as e:
        logger.error(f"{user_id} : {e}")
        return 500
