from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)

from helper.database import codeflixbots
from helper.scope import get_scope_id


def _callback_scope_id(query):
    chat = getattr(query.message, "chat", None)

    if chat:
        chat_type = getattr(chat, "type", None)
        type_name = str(
            getattr(chat_type, "value", chat_type)
        ).lower()

        if type_name.endswith("channel"):
            return int(chat.id)

    if query.from_user:
        return int(query.from_user.id)
    return int(query.message.chat.id)


@Client.on_message(
    (filters.private | filters.group | filters.channel) & filters.command("autorename")
)
async def auto_rename_command(client, message):
    scope_id = get_scope_id(message)

    command_text = message.text or ""
    command_parts = command_text.split(maxsplit=1)

    if len(command_parts) < 2 or not command_parts[1].strip():
        return await message.reply_text(
            "**Please provide a new name after /autorename.**\n\n"
            "**Example:**\n"
            "`/autorename Overflow [S{season}E{episode}] - [Dual] {quality}`"
        )

    format_template = command_parts[1].strip()

    await codeflixbots.set_format_template(
        scope_id,
        format_template,
    )

    await message.reply_text(
        "**✅ Auto Rename Format Saved**\n\n"
        "Send `/start` to activate quality rename mode, "
        "then send your files.\n\n"
        f"**Saved format:**\n`{format_template}`"
    )


@Client.on_message(
    (filters.private | filters.group | filters.channel) & filters.command("setmedia")
)
async def set_media_command(client, message):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📜 Documents", callback_data="setmedia_document")],
        [InlineKeyboardButton("🎬 Videos", callback_data="setmedia_video")],
        [InlineKeyboardButton("🎵 Audio", callback_data="setmedia_audio")],
    ])

    await message.reply_text(
        "✨ **Choose Your Media Preference** ✨\n"
        "Select the type of media you want the bot to upload:",
        reply_markup=keyboard,
    )


@Client.on_callback_query(filters.regex(r"^setmedia_"))
async def handle_media_selection(client, callback_query: CallbackQuery):
    scope_id = _callback_scope_id(callback_query)

    media_type = callback_query.data.split("_", 1)[1].lower()

    if media_type not in {"document", "video", "audio"}:
        return await callback_query.answer(
            "Invalid media type.",
            show_alert=True,
        )

    try:
        await codeflixbots.set_media_preference(
            scope_id,
            media_type,
        )

        await callback_query.answer(
            f"Media preference saved: {media_type}"
        )

        await callback_query.message.edit_text(
            "**✅ Media Preference Updated**\n\n"
            f"Your upload preference is now: **{media_type.title()}**"
        )

    except Exception as error:
        await callback_query.answer(
            "Could not save the media preference.",
            show_alert=True,
        )

        try:
            await callback_query.message.edit_text(
                f"**⚠️ Error saving media preference**\n\n"
                f"{str(error)[:400]}"
            )
        except Exception:
            pass
