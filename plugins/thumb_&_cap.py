import os
from pathlib import Path

from pyrogram import Client, filters
from helper.database import codeflixbots
from helper.scope import get_scope_id
from config import Config

THUMB_DIR = Path(Config.STORAGE_DIR) / "thumbnails"
THUMB_DIR.mkdir(parents=True, exist_ok=True)


@Client.on_message((filters.private | filters.group | filters.channel) & filters.command("set_caption"))
async def add_caption(client, message):
    scope_id = get_scope_id(message)
    if len(message.command) == 1:
        return await message.reply_text(
            "**Send a caption template.**\nExample: `/set_caption **{filename}**\nSize: {filesize}\nDuration: {duration}`"
        )
    caption = message.text.split(" ", 1)[1]
    await codeflixbots.set_caption(scope_id, caption=caption)
    await message.reply_text("**✅ Caption saved.**")


@Client.on_message((filters.private | filters.group | filters.channel) & filters.command("del_caption"))
async def delete_caption(client, message):
    scope_id = get_scope_id(message)
    caption = await codeflixbots.get_caption(scope_id)
    if not caption:
        return await message.reply_text("**You don't have a saved caption.**")
    await codeflixbots.set_caption(scope_id, caption=None)
    await message.reply_text("**🗑️ Caption deleted.**")


@Client.on_message((filters.private | filters.group | filters.channel) & filters.command(["see_caption", "view_caption"]))
async def see_caption(client, message):
    scope_id = get_scope_id(message)
    caption = await codeflixbots.get_caption(scope_id)
    await message.reply_text(f"**Your caption:**\n\n{caption}" if caption else "**No caption saved.**")


@Client.on_message((filters.private | filters.group | filters.channel) & filters.command(["view_thumb", "viewthumb"]))
async def viewthumb(client, message):
    scope_id = get_scope_id(message)
    saved_path = THUMB_DIR / f"{scope_id}.jpg"
    if saved_path.is_file():
        await client.send_photo(message.chat.id, str(saved_path), caption="**Saved thumbnail**")
        return
    thumb_id = await codeflixbots.get_thumbnail(scope_id)
    if thumb_id:
        await client.send_photo(chat_id=message.chat.id, photo=thumb_id)
    else:
        await message.reply_text("**You don't have a saved thumbnail.**")


@Client.on_message((filters.private | filters.group | filters.channel) & filters.command(["del_thumb", "delthumb"]))
async def removethumb(client, message):
    scope_id = get_scope_id(message)
    await codeflixbots.set_thumbnail(scope_id, file_id=None)
    saved_path = THUMB_DIR / f"{scope_id}.jpg"
    try:
        saved_path.unlink(missing_ok=True)
    except OSError:
        pass
    await message.reply_text("**🗑️ Thumbnail deleted.**")


@Client.on_message((filters.private | filters.group | filters.channel) & filters.photo)
async def addthumbs(client, message):
    scope_id = get_scope_id(message)
    status = await message.reply_text("**Saving thumbnail...**")
    saved_path = THUMB_DIR / f"{scope_id}.jpg"
    temp_path = None
    temp_output = THUMB_DIR / f"{scope_id}_new.jpg"
    try:
        temp_path = await client.download_media(message.photo.file_id, file_name=str(THUMB_DIR / f"{scope_id}_temp"))
        if not temp_path or not os.path.isfile(temp_path):
            raise RuntimeError("Could not download the photo")
        from PIL import Image
        with Image.open(temp_path) as image:
            image = image.convert("RGB")
            image.thumbnail((320, 320))
            for quality in (88, 78, 68, 58):
                image.save(temp_output, "JPEG", quality=quality, optimize=True)
                if temp_output.stat().st_size <= 190 * 1024:
                    break
        os.replace(temp_output, saved_path)
        await codeflixbots.set_thumbnail(scope_id, file_id=message.photo.file_id)
        await status.edit_text("**✅ Thumbnail saved permanently in bot storage.**")
    except Exception as error:
        await status.edit_text(f"**Could not save thumbnail:** {str(error)[:400]}")
    finally:
        for temporary in (temp_path, str(temp_output)):
            if temporary and os.path.isfile(temporary):
                try:
                    os.remove(temporary)
                except OSError:
                    pass
