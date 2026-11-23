# Auto Rename Bot — Batch Edition

Telegram file renamer and episode sorter. User settings, saved thumbnails, and pending `/filessort` queues are stored locally in SQLite; MongoDB is not used.

## Features

- Concurrent auto-renaming with a server-safe worker limit.
- Smart anime title, season, episode, and resolution detection.
- Safe unique temporary folders so simultaneous files cannot overwrite one another.
- Original extension retained; output names are sanitized against path traversal and invalid characters.
- Original media bytes and metadata are preserved by default. Optional metadata tagging uses FFmpeg stream-copy (`-c copy`) with no re-encoding; if remuxing fails, the unchanged original bytes are used.
- Saved custom thumbnails are stored locally under `storage/thumbnails/` and their Telegram `file_id` is also saved in SQLite.
- Download/upload progress bars show percentage, speed, transferred size, and ETA.
- `/filessort` + `/sort` is a separate workflow: it copies original Telegram messages in title → season → episode → quality order without renaming or downloading the files.
- Sort progress is tracked so retrying `/sort` only resends files that were not copied successfully.
- SQLite WAL mode provides persistent local storage without a remote database.

## Commands

| Command | Purpose |
|---|---|
| `/start` | Register and open the help menu |
| `/autorename FORMAT` | Save a filename template; future files are renamed and uploaded |
| `/filessort` | Begin collecting files for sorting only |
| `/sort` | Stop collection and copy queued files in title → season → episode → quality order |
| `/setmedia` | Choose output as document, video, or audio |
| `/metadata` | Toggle optional metadata tagging (off by default) |
| `/set_caption` | Save a custom caption using `{filename}`, `{filesize}`, `{duration}` |
| `/see_caption`, `/del_caption` | View/delete the caption |
| `/view_thumb`, `/del_thumb` | View/delete the saved thumbnail |
| `/settitle`, `/setauthor`, `/setartist`, `/setaudio`, `/setsubtitle`, `/setvideo` | Set metadata tag values |
| `/status` | Admin bot status |
| `/broadcast` | Admin broadcast (reply to a message) |
| `/restart` | Admin restart |

## Auto-rename

Example template:

```text
/autorename Naruto S{season}E{episode} {quality}
```

Send one or many files. The bot runs independent rename jobs concurrently, up to `MAX_CONCURRENT_FILES` (default 4, capped at 8). Each job gets its own temporary folder. The filename extension is retained. If the episode or season cannot be confidently parsed, the template substitutes `XX` rather than inventing a number.

## File sorting (no rename)

1. Send `/filessort`.
2. Send all files in any order.
3. Send `/sort`.

The bot groups matching titles, sorts seasons and episodes numerically, then sorts quality from 360p → 480p → 720p → 1080p → 1440p → 2160p. The episode heading and quality caption are bold. The original Telegram media message is copied; its file name and media content are not changed. If a few copies fail, send `/sort` again to retry only those files.

## Runtime environment

When a Pyrogram session file already exists in persistent storage, the deployment needs only these three user-supplied environment variables:

```env
BOT_TOKEN=your_botfather_token
OWNER_ID=your_telegram_numeric_user_id
ADMIN_ID=123456789,987654321
```

`OWNER_ID` is automatically added to the administrator list. `ADMIN_ID` accepts IDs separated by spaces or commas.

### One-time Pyrogram session setup

This project keeps Pyrogram/MTProto so it can handle larger Telegram media files. Pyrogram still needs a Telegram API ID and API hash once to create the initial bot session. A bot token does not replace those app credentials. To keep the *deployment environment* limited to the three variables above:

1. Copy `.env.first-run.example` to `.env` and temporarily fill `BOT_TOKEN`, `OWNER_ID`, `ADMIN_ID`, `API_ID`, and `API_HASH`.
2. Install requirements, then run `python generate_session.py` once. This creates `storage/auto_rename_bot.session`.
3. Keep that session file private. Copy it into the deployment's persistent `STORAGE_DIR` before starting the bot.
4. Deploy with only `BOT_TOKEN`, `OWNER_ID`, and `ADMIN_ID`. Do not delete or replace the session file between restarts.

Alternatively, for Render, add `API_ID` and `API_HASH` temporarily in the service environment for the first startup. The bot will create `auto_rename_bot.session` on its `/var/data` persistent disk. After it starts successfully, remove those two temporary variables and redeploy; subsequent starts use only the three variables shown above. Render supports shell/SCP transfer to a paid background worker if you create the session locally instead. If the session file is missing on a clean deployment, the bot stops with a clear error rather than silently failing later.

### Optional tuning

```env
MAX_CONCURRENT_FILES=4
MAX_CONCURRENT_TRANSMISSIONS=4
STORAGE_DIR=storage
TEMP_DIR=/tmp
WEBHOOK=False
```

Raise concurrency only if the server has enough RAM, CPU, disk throughput, and network capacity. The application caps both worker settings at 8 to avoid unbounded task creation pressure. For Render, `render.yaml` declares a persistent disk mounted at `/var/data` and sets `STORAGE_DIR` automatically.

## Install and run

Python 3.10 is recommended. FFmpeg is installed by the Dockerfile and is only used when optional metadata tagging is enabled. Without FFmpeg, files can still be renamed and uploaded with their original media bytes.

```bash
pip install -r requirements.txt
# For a brand-new bot session, first use .env.first-run.example as .env,
# fill all five values, and run the one-time session setup:
python generate_session.py
# Then use .env.example as .env with only BOT_TOKEN, OWNER_ID and ADMIN_ID.
python bot.py
```

If a valid `storage/auto_rename_bot.session` already exists, skip `generate_session.py` and use only `.env.example`.

For Docker:

```bash
docker build -t auto-rename-bot .
docker run --env-file .env -v auto-rename-data:/app/storage auto-rename-bot
```

## Tests

```bash
python -m unittest discover -s tests -v
python -m compileall -q .
python -m json.tool app.json
```

## Storage

- SQLite database: `storage/bot.sqlite3`
- Saved thumbnails: `storage/thumbnails/<telegram_user_id>.jpg`
- Pyrogram authorization session: `storage/auto_rename_bot.session`
- Temporary rename files are created under the system temp directory (`/tmp` by default) and removed after each job; they are not stored on the persistent data disk.
- `/filessort` stores only source chat/message references and sort state; it does not duplicate media on disk.
- Keep the storage directory on a persistent disk when deploying. It contains the database, thumbnails, and bot authorization session.
