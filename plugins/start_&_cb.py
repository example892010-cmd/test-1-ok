import asyncio

from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CallbackQuery,
)

from helper.database import codeflixbots
from helper.scope import get_scope_id
from plugins.rename_session import activate_rename_session
from config import Config, Txt


def _home_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("• ᴍʏ ᴀʟʟ ᴄᴏᴍᴍᴀɴᴅs •", callback_data="help")],
        [
            InlineKeyboardButton("• ᴜᴘᴅᴀᴛᴇs", url="https://t.me/Codeflix_Bots"),
            InlineKeyboardButton("sᴜᴘᴘᴏʀᴛ •", url="https://t.me/CodeflixSupport"),
        ],
        [
            InlineKeyboardButton("• ᴀʙᴏᴜᴛ", callback_data="about"),
            InlineKeyboardButton("sᴏᴜʀᴄᴇ •", callback_data="source"),
        ],
    ])


def _help_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("• ᴀᴜᴛᴏ ʀᴇɴᴀᴍᴇ ғᴏʀᴍᴀᴛ •", callback_data="file_names")],
        [
            InlineKeyboardButton("• ᴛʜᴜᴍʙɴᴀɪʟ", callback_data="thumbnail"),
            InlineKeyboardButton("ᴄᴀᴘᴛɪᴏɴ •", callback_data="caption"),
        ],
        [
            InlineKeyboardButton("• ᴍᴇᴛᴀᴅᴀᴛᴀ", callback_data="meta"),
            InlineKeyboardButton("ᴅᴏɴᴀᴛᴇ •", callback_data="donate"),
        ],
        [InlineKeyboardButton("• ʜᴏᴍᴇ", callback_data="home")],
    ])


def _callback_scope_id(query):
    """
    Channel buttons use the channel ID.
    Private/Group buttons use the clicking user's ID or chat ID.
    """
    chat = getattr(query.message, "chat", None)

    if chat:
        chat_type = getattr(chat, "type", None)
        type_name = str(
            getattr(chat_type, "value", chat_type)
        ).lower()

        if type_name.endswith("channel"):
            return int(chat.id)

    return int(query.from_user.id)


async def _edit_page(
    message,
    text,
    reply_markup=None,
    disable_web_page_preview=True,
):
    if getattr(message, "media", None):
        return await message.edit_caption(
            caption=text,
            reply_markup=reply_markup,
        )

    return await message.edit_text(
        text=text,
        reply_markup=reply_markup,
        disable_web_page_preview=disable_web_page_preview,
    )


@Client.on_message(
    (filters.private | filters.group | filters.channel) & filters.command("start")
)
async def start(client: Client, message: Message):
    scope_id = get_scope_id(message)

    activate_rename_session(scope_id, "quality")

    await codeflixbots.add_user(client, message)

    user = message.from_user
    display_name = (
        user.mention
        if user
        else (getattr(message.chat, "title", None) or "Chat")
    )

    welcome_text = (
        Txt.START_TXT.format(display_name)
        + "\n\n"
        + "**✅ Quality Rename Mode Activated**\n\n"
        + "Send your files here. I will rename and upload them "
          "using your saved format, with quality and episode headings."
    )

    buttons = _home_keyboard()

    if Config.START_PIC:
        try:
            await message.reply_photo(
                Config.START_PIC,
                caption=welcome_text,
                reply_markup=buttons,
            )
            return
        except Exception:
            pass

    await message.reply_text(
        welcome_text,
        reply_markup=buttons,
        disable_web_page_preview=True,
    )


@Client.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
    data = query.data or ""
    scope_id = _callback_scope_id(query)

    if data in {"close", "close_data"}:
        await query.answer()
        try:
            await query.message.delete()
        except Exception:
            pass
        return

    if data == "home":
        text = Txt.START_TXT.format(query.from_user.mention)
        keyboard = _home_keyboard()

    elif data == "help":
        text = Txt.HELP_TXT
        keyboard = _help_keyboard()

    elif data == "caption":
        text = Txt.CAPTION_TXT
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("• ʙᴀᴄᴋ •", callback_data="help")]
        ])

    elif data == "file_names":
        template = await codeflixbots.get_format_template(scope_id)
        text = Txt.FILE_NAME_TXT + (
            f"\n\n**Saved format:** `{template}`"
            if template else ""
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("• ʙᴀᴄᴋ •", callback_data="help")]
        ])

    elif data == "thumbnail":
        text = Txt.THUMBNAIL_TXT
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("• ʙᴀᴄᴋ •", callback_data="help")]
        ])

    elif data in {"meta", "metadatax"}:
        text = Txt.SEND_METADATA
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("• ʙᴀᴄᴋ •", callback_data="help")]
        ])

    elif data == "donate":
        text = Txt.DONATE_TXT
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("• ʙᴀᴄᴋ •", callback_data="help")]
        ])

    elif data == "source":
        text = Txt.SOURCE_TXT
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("• ʙᴀᴄᴋ •", callback_data="home")]
        ])

    elif data == "about":
        text = Txt.ABOUT_TXT
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "• sᴜᴘᴘᴏʀᴛ",
                    url="https://t.me/CodeflixSupport",
                ),
                InlineKeyboardButton(
                    "ᴄᴏᴍᴍᴀɴᴅs •",
                    callback_data="help",
                ),
            ],
            [InlineKeyboardButton("• ʙᴀᴄᴋ •", callback_data="home")],
        ])

    else:
        return await query.answer(
            "Unknown menu action",
            show_alert=False,
        )

    try:
        await _edit_page(query.message, text, keyboard)
        await query.answer()
    except Exception as error:
        await query.answer(
            f"Could not open this menu: {str(error)[:150]}",
            show_alert=True,
        )


@Client.on_message(
    (filters.private | filters.group | filters.channel) & filters.command("help")
)
async def help_command(client, message):
    await message.reply_text(
        text=Txt.HELP_TXT,
        disable_web_page_preview=True,
        reply_markup=_help_keyboard(),
    )
