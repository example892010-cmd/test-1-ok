import math
import os
import time
from datetime import datetime
from pathlib import Path

from pytz import timezone

from config import Config, Txt

_PROGRESS_LAST_UPDATE = {}


def humanbytes(size):
    if size is None:
        return "0 B"
    size = float(size)
    units = ("B", "KB", "MB", "GB", "TB", "PB")
    index = 0
    while size >= 1024 and index < len(units) - 1:
        size /= 1024
        index += 1
    return f"{size:.2f} {units[index]}"


def TimeFormatter(milliseconds: int) -> str:
    seconds = max(0, int(milliseconds // 1000))
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    parts = []
    if days: parts.append(f"{days}d")
    if hours: parts.append(f"{hours}h")
    if minutes: parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")
    return " ".join(parts)


async def progress_for_pyrogram(current, total, ud_type, message, start):
    if not total:
        return
    now = time.monotonic()
    message_key = (getattr(getattr(message, "chat", None), "id", 0), getattr(message, "id", id(message)))
    last_update = _PROGRESS_LAST_UPDATE.get(message_key, 0.0)
    if now - last_update < 2.0 and current < total:
        return
    _PROGRESS_LAST_UPDATE[message_key] = now

    elapsed = max(now - start, 0.001)
    percentage = min(100.0, current * 100.0 / total)
    speed = current / elapsed
    eta = max(0, (total - current) / speed) if speed > 0 else 0
    filled = min(20, int(percentage // 5))
    bar = "█" * filled + "░" * (20 - filled)
    text = (
        f"**{ud_type}**\n\n{bar}\n"
        + Txt.PROGRESS_BAR.format(
            round(percentage, 1),
            humanbytes(current),
            humanbytes(total),
            humanbytes(speed),
            TimeFormatter(eta * 1000),
        )
    )
    try:
        await message.edit_text(text)
    except Exception:
        # Progress updates must never interrupt a transfer.
        pass
    finally:
        if current >= total:
            _PROGRESS_LAST_UPDATE.pop(message_key, None)


def clear_progress_for_message(message):
    """Remove throttling state after a transfer ends or fails."""
    message_key = (
        getattr(getattr(message, "chat", None), "id", 0),
        getattr(message, "id", id(message)),
    )
    _PROGRESS_LAST_UPDATE.pop(message_key, None)


async def send_log(bot, user):
    if Config.LOG_CHANNEL is None:
        return
    curr = datetime.now(timezone("Asia/Kolkata"))
    date_text = curr.strftime("%d %B, %Y")
    time_text = curr.strftime("%I:%M:%S %p")
    await bot.send_message(
        Config.LOG_CHANNEL,
        f"**NEW USER STARTED THE BOT**\n\nUser: {user.mention}\nID: `{user.id}`\n"
        f"Username: @{user.username or 'none'}\nDate: {date_text}\nTime: {time_text}",
    )


def convert(seconds):
    seconds = max(0, int(seconds)) % (24 * 3600)
    hour, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hour}:{minutes:02d}:{seconds:02d}"


def add_prefix_suffix(input_string, prefix="", suffix=""):
    path = Path(input_string)
    return f"{prefix or ''}{path.stem}{(' ' + suffix) if suffix else ''}{path.suffix}"
