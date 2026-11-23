import asyncio

from pyrogram import Client, filters

from helper.scope import get_scope_id


# Settings are kept separately for each user, group, or channel.
_RENAME_MODES = {}
_OUTPUT_LOCKS = {}
_LAST_QUALITY = {}
_GETLINKAUTO_SENT = set()


def activate_rename_session(scope_id, mode="quality"):
    """Activate or reset a rename session."""
    scope_id = int(scope_id)

    if mode not in {"quality", "normal"}:
        raise ValueError("Invalid rename mode.")

    _RENAME_MODES[scope_id] = mode
    _LAST_QUALITY.pop(scope_id, None)
    _GETLINKAUTO_SENT.discard(scope_id)


def get_rename_mode(scope_id):
    return _RENAME_MODES.get(int(scope_id))


def get_output_lock(scope_id):
    scope_id = int(scope_id)

    if scope_id not in _OUTPUT_LOCKS:
        _OUTPUT_LOCKS[scope_id] = asyncio.Lock()

    return _OUTPUT_LOCKS[scope_id]


def get_last_quality(scope_id):
    return _LAST_QUALITY.get(int(scope_id))


def set_last_quality(scope_id, quality):
    _LAST_QUALITY[int(scope_id)] = quality


def has_sent_getlinkauto(scope_id):
    return int(scope_id) in _GETLINKAUTO_SENT


def mark_getlinkauto_sent(scope_id):
    _GETLINKAUTO_SENT.add(int(scope_id))


@Client.on_message(
    (filters.private | filters.group | filters.channel) & filters.command("normalrename")
)
async def normal_rename_mode(client, message):
    scope_id = get_scope_id(message)

    activate_rename_session(scope_id, "normal")

    await message.reply_text(
        "**✅ Normal Rename Mode Activated**\n\n"
        "Files will be renamed using your saved template.\n"
        "Quality headings and episode headings will not be sent.\n\n"
        "Send your files to begin."
    )
