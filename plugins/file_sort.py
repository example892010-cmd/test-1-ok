"""Collect files with /filessort and re-send them in episode/quality order with /sort."""
import asyncio
import logging
from collections import defaultdict

from pyrogram import Client, filters
from pyrogram.errors import FloodWait

from helper.database import codeflixbots
from helper.scope import get_scope_id
from helper.filename_utils import media_sort_key, parse_media_name

logger = logging.getLogger(__name__)
_active_sorters = set()


async def _send_message_with_floodwait(client, chat_id, text):
    while True:
        try:
            return await client.send_message(chat_id, text)
        except FloodWait as error:
            await asyncio.sleep(error.value + 1)


async def _copy_message_with_floodwait(client, chat_id, item, caption):
    while True:
        try:
            return await client.copy_message(
                chat_id=chat_id,
                from_chat_id=item["chat_id"],
                message_id=item["message_id"],
                caption=caption,
            )
        except FloodWait as error:
            await asyncio.sleep(error.value + 1)


@Client.on_message((filters.private | filters.group | filters.channel) & filters.command("filessort"))
async def begin_file_sort(client, message):
    scope_id = get_scope_id(message)
    await codeflixbots.start_sort_session(scope_id)
    await message.reply_text(
        "**📂 File sorting mode started.**\n\n"
        "Send all your files in any order. I will keep their original names and metadata.\n\n"
        "When finished, send **/sort**."
    )


@Client.on_message((filters.private | filters.group | filters.channel) & filters.command("sort"))
async def sort_collected_files(client, message):
    scope_id = get_scope_id(message)
    if scope_id in _active_sorters:
        return await message.reply_text("**A sort operation is already running for you.**")

    _active_sorters.add(scope_id)
    try:
        await codeflixbots.stop_sort_session(scope_id)
        files = await codeflixbots.get_sort_files(scope_id)
        if not files:
            await codeflixbots.finish_sort_session(scope_id)
            return await message.reply_text("**No files are queued. Start with /filessort.**")

        prepared = []
        for index, item in enumerate(files):
            parsed = parse_media_name(item["file_name"])
            prepared.append({**item, "parsed": parsed, "index": index})

        series_groups = defaultdict(list)
        for item in prepared:
            key = " ".join(item["parsed"].title.casefold().split())
            series_groups[key].append(item)

        status = await message.reply_text(f"**🔃 Sorting {len(prepared)} file(s)...**")
        sent = 0
        failed = 0
        try:
            for _series_key, series_files in sorted(series_groups.items(), key=lambda pair: pair[0]):
                display_title = series_files[0]["parsed"].title
                await _send_message_with_floodwait(
                    client, message.chat.id, f"**📁 {display_title}**"
                )

                series_files.sort(
                    key=lambda item: media_sort_key(item["parsed"], item["index"])
                )
                current_episode = object()
                for item in series_files:
                    parsed = item["parsed"]
                    episode_identity = (parsed.season, parsed.episode)
                    if episode_identity != current_episode:
                        current_episode = episode_identity
                        if parsed.episode is None:
                            heading = "**Episode not detected 👇**"
                        else:
                            prefix = f"S{parsed.season:02d} " if parsed.season is not None else ""
                            heading = f"**{prefix}Episode {parsed.episode:02d} 👇**"
                        await _send_message_with_floodwait(client, message.chat.id, heading)

                    quality_label = parsed.quality or "Quality unknown"
                    caption = f"**{quality_label}**"
                    try:
                        await _copy_message_with_floodwait(
                            client, message.chat.id, item, caption
                        )
                        await codeflixbots.mark_sort_file_sent(
                            scope_id, item["chat_id"], item["message_id"]
                        )
                        sent += 1
                    except Exception as error:
                        failed += 1
                        logger.warning("Could not copy queued file %s: %s", item["file_name"], error)

                    processed = sent + failed
                    if processed % 10 == 0 or processed == len(prepared):
                        percentage = int(processed * 100 / len(prepared))
                        filled = min(20, percentage // 5)
                        bar = "█" * filled + "░" * (20 - filled)
                        await status.edit_text(
                            f"**🔃 Sorting files**\n\n{bar}\n**Progress:** {processed}/{len(prepared)} "
                            f"({percentage}%)\n**Sent:** {sent} • **Failed:** {failed}"
                        )

            if failed == 0:
                await codeflixbots.finish_sort_session(scope_id)
                completion_note = "All queued files were copied successfully."
            else:
                completion_note = (
                    "Failed items remain queued. Send **/sort** again to retry only the files "
                    "that were not copied; already-sent files will not be duplicated."
                )
            await status.edit_text(
                f"**✅ File sorting run finished**\n\n**Queued this run:** {len(files)}\n"
                f"**Sent:** {sent}\n**Failed:** {failed}\n\n{completion_note}"
            )
        except Exception as error:
            logger.exception("File sort operation stopped")
            await status.edit_text(
                f"**Sorting stopped:** {str(error)[:700]}\n\nCopied: {sent} / {len(files)}\n"
                "Files not yet copied remain queued for another **/sort**."
            )
    finally:
        _active_sorters.discard(scope_id)
