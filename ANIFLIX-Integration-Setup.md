# ANIFLIX File Store + Auto Poster integration patch

This patch connects the two existing Telegram bots without combining their runtimes or databases. The File Store Bot continues to use its current SQLite database and archive/storage channel. The Auto Poster continues to use its current MongoDB database and existing publishing configuration.

**The existing Auto Poster publishing function is not rewritten.** The authenticated bridge calls `plugins/file_rename.py::_publish_batch1renamed_link` as-is. Existing Anime Post and Ongoing channels, poster settings, caption/button templates, FSUB, admin panel, and existing commands are preserved.

## Resulting admin workflow

1. Add the **File Store Bot** as an administrator to the private upload channel. Keep its existing administrator access to its archive/storage channel.
2. Upload exactly three files for one anime episode: 480p, 720p, and 1080p. They can arrive in any order.
3. Quality matching uses `480p`, `720p`, or `1080p` in the filename/caption. If the upload is sent as a Telegram video (not as a document), the bot can also use Telegram's video height. A document with no quality label cannot be safely identified; give it a quality label in its filename or caption. The bot will not guess quality from upload order.
4. After all three files have been acknowledged, send this command in the upload channel (or send it privately to the File Store Bot as a configured admin):

   ```text
   /batch1renamed
   NARUTO SHIPPUDEN
   Season 18
   Epi 365
   ```

   `365`, `01`, `25`, and numeric episode ranges are accepted. The entered episode digits are preserved for the existing Auto Poster templates. Do **not** add a link; the File Store Bot generates it.

5. The File Store Bot matches the three staged messages to their detected qualities, archives the exact original Telegram messages using its current `Storage.store_message()` system, verifies the archive copies, writes an ordered batch manifest (480p, 720p, 1080p), and creates its normal `https://t.me/<FILE_STORE_BOT>?start=batch_...` link.
6. The File Store Bot sends a signed HTTPS request to Auto Poster. Auto Poster invokes its existing link-only publisher, which handles the configured Anime Post and Ongoing destinations independently and uses the existing templates, posters, buttons, and invite-link logic.
7. The File Store Bot reports the generated link and the Auto Poster response. If the network handoff fails before Auto Poster claims the event, send the same command again; the saved batch link is reused rather than archiving the files again. Duplicate episode events are blocked by a stable anime/season/episode key.

## Render environment settings

Use one long random shared secret on both services. Keep each service's existing bot token and existing database settings.

### File Store Bot Render service

Keep all current settings and add:

- `UPLOAD_CHANNEL_ID`: private upload channel ID in `-100...` format.
- `AUTO_POSTER_BRIDGE_URL`: full HTTPS URL of the Auto Poster Render service plus `/internal/file-store/batch1renamed`. Example path: `https://YOUR-AUTO-POSTER-SERVICE.onrender.com/internal/file-store/batch1renamed`.
- `AUTO_POSTER_BRIDGE_SECRET`: the shared secret.

### Auto Poster Render service

Keep all current settings and add:

- `FILE_STORE_BRIDGE_SECRET`: exactly the same shared secret.
- Keep `WEBHOOK=true`, because the existing HTTP health server also hosts the private bridge endpoint.
- Add the File Store Bot's `OWNER_ID` to the existing Auto Poster `ADMIN` environment setting (comma- or space-separated numeric Telegram user IDs). The bridge refuses to publish unless this user is authorized by the existing Auto Poster admin check.

Do not replace either bot token, either database URI/path, or the File Store archive channel ID.

## Telegram permissions

- **File Store Bot:** administrator in the private upload channel and its current archive/storage channel. It must be able to read the upload-channel messages by ID and post/copy messages to the archive channel.
- **Auto Poster Bot:** keep its existing admin/posting permissions in the configured Anime Post and Ongoing channels. It does not need to be added to the upload channel; the services communicate over authenticated HTTPS.
- Restrict who can post in the private upload channel to trusted admins. Telegram channel-post updates may not identify the human author, so a `/batch1renamed` command posted directly in that channel is attributed to the configured File Store `OWNER_ID`. A private command sent directly to the File Store Bot is checked against its admin list.

## Data preservation and migration

- File Store continues using `SQLITE_PATH` and the current archive/storage channel. SQLite schema version 2 adds only `upload_candidates` and `upload_batches`; existing state snapshots, file records, link records, and archive messages are not dropped or rewritten. Existing migration backup behavior creates `<SQLITE_PATH>.pre-migration.bak` before the schema update when applicable.
- Auto Poster continues using its current MongoDB `DB_URL` and `DB_NAME`. The bridge adds one collection, `file_store_bridge_events`, for event idempotency; it does not migrate or replace existing collections.
- The projects remain two separate Render services with separate dependency sets and bot identities. The connection is automatic; no one needs to copy the generated link manually.
- The patch files are provided separately for each repository. Extract each patch into the root of its matching existing repository and allow replacement of the listed files.

## Verification status and deployment boundary

- Python compilation passed for both repositories.
- Auto Poster complete offline suite: **44/44 passed**.
- File Store complete offline suite: **71 passed; 8 runtime-dependent checks could not run** because Pyrogram/pyrofork is not installed in this execution environment. The 8 test errors all report `ModuleNotFoundError: pyrogram`; the environment could not reach PyPI to install the repository's declared dependency. The focused integration, parser, SQLite migration, idempotency, configuration, and channel-filter tests passed.
- Bridge runtime tests use fake MongoDB collections and a fake publisher to verify authentication, payload handling, dispatch, and duplicate suppression. They are not live Telegram tests.
- No live Telegram sends, MongoDB production operations, Render deployments, or GitHub updates were performed. After setting the environment variables and permissions, test one real episode before normal use.
