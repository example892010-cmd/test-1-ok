import os
import re
import tempfile
import time


def _parse_ids(value):
    result = []
    for token in re.split(r"[\s,]+", value or ""):
        if token.strip():
            try:
                result.append(int(token.strip()))
            except ValueError:
                raise ValueError(f"Invalid Telegram user ID: {token!r}")
    return list(dict.fromkeys(result))


def _as_bool(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


class Config:
    API_ID = os.getenv("API_ID", "").strip()
    API_HASH = os.getenv("API_HASH", "").strip()
    BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

    OWNER_ID = int(os.getenv("OWNER_ID", "0") or 0)
    ADMIN_ID_RAW = os.getenv("ADMIN_ID", "").strip()
    ADMIN_IDS = _parse_ids(ADMIN_ID_RAW)
    if OWNER_ID:
        ADMIN_IDS = list(dict.fromkeys([OWNER_ID, *ADMIN_IDS]))
    # Backwards-compatible name used by the original plugins.
    ADMIN = ADMIN_IDS

    STORAGE_DIR = os.getenv("STORAGE_DIR", "storage")
    TEMP_DIR = os.getenv("TEMP_DIR", tempfile.gettempdir())
    PORT = int(os.getenv("PORT", "8080"))
    BOT_UPTIME = time.time()
    START_PIC = os.getenv("START_PIC", "https://graph.org/file/29a3acbbab9de5f45a5fe.jpg")
    LOG_CHANNEL_RAW = os.getenv("LOG_CHANNEL", "").strip()
    LOG_CHANNEL = int(LOG_CHANNEL_RAW) if LOG_CHANNEL_RAW else None
    FORCE_SUB_CHANNELS = [x.strip().lstrip("@") for x in os.getenv("FORCE_SUB_CHANNELS", "").split(",") if x.strip()]
    WEBHOOK = _as_bool(os.getenv("WEBHOOK"), False)
    MAX_CONCURRENT_FILES = max(1, min(8, int(os.getenv("MAX_CONCURRENT_FILES", "4"))))
    MAX_CONCURRENT_TRANSMISSIONS = max(1, min(8, int(os.getenv("MAX_CONCURRENT_TRANSMISSIONS", "4"))))

    @classmethod
    def validate(cls):
        missing = []
        session_file = os.path.join(cls.STORAGE_DIR, "auto_rename_bot.session")
        has_existing_session = os.path.isfile(session_file)
        for name in ("BOT_TOKEN",):
            if not getattr(cls, name):
                missing.append(name)
        # Pyrogram requires an API ID/hash when creating a first-time bot session.
        # A previously authorized session can be restarted without these values.
        if not has_existing_session:
            for name in ("API_ID", "API_HASH"):
                if not getattr(cls, name):
                    missing.append(name)
        elif bool(cls.API_ID) != bool(cls.API_HASH):
            raise RuntimeError("Set both API_ID and API_HASH together, or remove both when reusing an existing session")
        if not cls.OWNER_ID:
            missing.append("OWNER_ID")
        if not cls.ADMIN_ID_RAW:
            missing.append("ADMIN_ID")
        if missing:
            raise RuntimeError("Missing required environment variable(s): " + ", ".join(missing))
        if cls.API_ID:
            try:
                int(cls.API_ID)
            except ValueError as error:
                raise RuntimeError("API_ID must be an integer") from error


class Txt:
    START_TXT = """<b>ʜᴇʏ! {}

» ɪ ᴀᴍ ᴀɴ ᴀᴅᴠᴀɴᴄᴇᴅ ʀᴇɴᴀᴍᴇ ʙᴏᴛ! ɪ ᴄᴀɴ ᴀᴜᴛᴏ-ʀᴇɴᴀᴍᴇ ʏᴏᴜʀ ғɪʟᴇs ᴡɪᴛʜ ᴄᴜsᴛᴏᴍ ᴄᴀᴘᴛɪᴏɴs ᴀɴᴅ ᴛʜᴜᴍʙɴᴀɪʟs, ᴀɴᴅ sᴏʀᴛ ᴛʜᴇᴍ ʙʏ ᴇᴘɪsᴏᴅᴇ ᴀɴᴅ ǫᴜᴀʟɪᴛʏ.</b>"""

    FILE_NAME_TXT = """<b>» <u>sᴇᴛᴜᴘ ᴀᴜᴛᴏ ʀᴇɴᴀᴍᴇ ғᴏʀᴍᴀᴛ</u></b>

<b>ᴠᴀʀɪᴀʙʟᴇs:</b>
➲ <code>{title}</code> — detected anime title
➲ <code>{season}</code> — season number
➲ <code>{episode}</code> — episode number
➲ <code>{quality}</code> — detected resolution

<b>Example:</b>
<code>/autorename Naruto S{season}E{episode} {quality}</code>

Send your files after setting the template. Files are processed concurrently.</b>"""

    ABOUT_TXT = """<b>❍ ɴᴀᴍᴇ : Auto Rename Bot
❍ ʟᴀɴɢᴜᴀɢᴇ : Python
❍ ᴅᴀᴛᴀʙᴀsᴇ : Local SQLite storage
❍ ʜᴏsᴛᴇᴅ ᴏɴ : Your server
❍ ᴜᴘᴅᴀᴛᴇs : @codeflix_bots

➻ ᴄʟɪᴄᴋ ᴛʜᴇ ʙᴜᴛᴛᴏɴs ʙᴇʟᴏᴡ ғᴏʀ ʜᴇʟᴘ ᴀɴᴅ ɪɴғᴏ.</b>"""

    THUMBNAIL_TXT = """<b><u>» sᴇᴛ ᴀ ᴄᴜsᴛᴏᴍ ᴛʜᴜᴍʙɴᴀɪʟ</u></b>

Send any photo to save it as your thumbnail.
/view_thumb — view your saved thumbnail
/del_thumb — delete your saved thumbnail

If no custom thumbnail is saved, the bot tries to use the original file thumbnail."""

    CAPTION_TXT = """<b><u>» sᴇᴛ ᴀ ᴄᴜsᴛᴏᴍ ᴄᴀᴘᴛɪᴏɴ</u></b>

Supported variables: <code>{filename}</code>, <code>{filesize}</code>, <code>{duration}</code>
Legacy variables: <code>{ꜰɪʟᴇɴᴀᴍᴇ}</code>, <code>{ꜰɪʟᴇsɪᴢᴇ}</code>

/set_caption — save a caption
/see_caption — view it
/del_caption — delete it"""

    PROGRESS_BAR = "\n\n<b>» Size</b> : {1} | {2}\n<b>» Done</b> : {0}%\n<b>» Speed</b> : {3}/s\n<b>» ETA</b> : {4}"

    DONATE_TXT = """<blockquote>ᴛʜᴀɴᴋs ғᴏʀ sʜᴏᴡɪɴɢ ɪɴᴛᴇʀᴇsᴛ ɪɴ ᴅᴏɴᴀᴛɪᴏɴ</blockquote>

<b><i>💞 ɪғ ʏᴏᴜ ʟɪᴋᴇ ᴏᴜʀ ʙᴏᴛ, ʏᴏᴜ ᴄᴀɴ sᴜᴘᴘᴏʀᴛ ɪᴛs ᴅᴇᴠᴇʟᴏᴘᴍᴇɴᴛ.</i></b>

<u>ᴜᴘɪ ɪᴅ</u> : <code>LodaLassan@fam</code>

Send a payment screenshot to the bot and reply with /bought."""

    PREMIUM_TXT = """<b>ᴜᴘɢʀᴀᴅᴇ ᴛᴏ ᴏᴜʀ ᴘʀᴇᴍɪᴜᴍ sᴇʀᴠɪᴄᴇ ᴀɴᴅ ᴇɴᴊᴏʏ ᴇxᴄʟᴜsɪᴠᴇ ғᴇᴀᴛᴜʀᴇs:
○ ᴜɴʟɪᴍɪᴛᴇᴅ ʀᴇɴᴀᴍɪɴɢ
○ ᴇᴀʀʟʏ ᴀᴄᴄᴇss ᴛᴏ ᴜᴘᴅᴀᴛᴇs

ᴛᴏ ᴀsᴋ ᴀʙᴏᴜᴛ ᴘʀᴇᴍɪᴜᴍ, ᴄᴏɴᴛᴀᴄᴛ @sewxiy.</b>"""

    PREPLANS_TXT = """<b>🎖️ ᴀᴠᴀɪʟᴀʙʟᴇ ᴘʟᴀɴs

For plan information and hosting enquiries, contact @ProYato.

For payment verification, upload the screenshot and reply with /bought.</b>"""

    HELP_TXT = """<b>ʜᴇʀᴇ ᴀʀᴇ ᴛʜᴇ ᴍᴀɪɴ ᴄᴏᴍᴍᴀɴᴅs:

/autorename FORMAT — set an auto-rename template
/filessort — start collecting files for sorting only
/sort — sort queued files by anime, season, episode and quality (no rename)
/setmedia — choose document, video or audio output
/metadata — toggle optional metadata tagging
/set_caption — set a custom caption
/see_caption — view saved caption
/del_caption — delete saved caption
/view_thumb — view saved thumbnail
/del_thumb — delete saved thumbnail

Admin commands: /status, /broadcast, /restart</b>"""

    SEND_METADATA = """<b>--Metadata Settings--</b>

/metadata: Turn optional metadata tagging on or off.

The default is Off, so the original media bytes and metadata remain untouched. When enabled, FFmpeg uses stream-copy without re-encoding."""

    SOURCE_TXT = """<b>ʜᴇʏ, ᴛʜɪs ɪs ᴀɴ ᴏᴘᴇɴ-sᴏᴜʀᴄᴇ ᴛᴇʟᴇɢʀᴀᴍ ᴀᴜᴛᴏ-ʀᴇɴᴀᴍᴇ ʙᴏᴛ.</b>

Written in Python with Pyrogram. Settings and queues are stored in local SQLite; MongoDB is not used.

<b>Source:</b> https://github.com/codeflix_bots/autorenamebot
<b>License:</b> MIT"""

    META_TXT = """**ᴍᴀɴᴀɢɪɴɢ ᴍᴇᴛᴀᴅᴀᴛᴀ ғᴏʀ ʏᴏᴜʀ ᴠɪᴅᴇᴏs ᴀɴᴅ ғɪʟᴇs**

**ᴍᴇᴛᴀᴅᴀᴛᴀ ғɪᴇʟᴅs:**
- **Title**: Descriptive media title.
- **Author**: Creator or owner.
- **Artist**: Artist associated with the media.
- **Audio**: Audio stream title.
- **Subtitle**: Subtitle stream title.
- **Video**: Video stream title.

**Commands:**
/settitle, /setauthor, /setartist, /setaudio, /setsubtitle, /setvideo

Metadata changes use stream-copy (no re-encoding). Original streams are retained where supported by the container."""
