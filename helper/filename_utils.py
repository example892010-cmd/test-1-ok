"""Pure helpers for safe media filename parsing and episode sorting."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

_INVALID_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|\x00-\x1f]')
_INVISIBLE_CHARS = re.compile(r"[\u200b-\u200d\ufeff]")
_SPACE_RUN = re.compile(r"[\s._-]+")

# Use ASCII alphanumeric boundaries instead of \b / \w so underscore-separated
# Telegram filenames (e.g. _S01E04_Tamil_480p_) parse accurately.
QUALITY_PATTERNS = [
    (re.compile(r"(?<![A-Za-z0-9])(2160p|4k|uhd)(?![A-Za-z0-9])", re.I), "2160p"),
    (re.compile(r"(?<![A-Za-z0-9])(1440p|2k)(?![A-Za-z0-9])", re.I), "1440p"),
    (re.compile(r"(?<![A-Za-z0-9])(1080p)(?![A-Za-z0-9])", re.I), "1080p"),
    (re.compile(r"(?<![A-Za-z0-9])(720p)(?![A-Za-z0-9])", re.I), "720p"),
    (re.compile(r"(?<![A-Za-z0-9])(480p)(?![A-Za-z0-9])", re.I), "480p"),
    (re.compile(r"(?<![A-Za-z0-9])(360p)(?![A-Za-z0-9])", re.I), "360p"),
]

SEASON_EPISODE_PATTERNS = [
    re.compile(
        r"(?i)(?<![A-Za-z0-9])(?:Season|S)[\s._-]*(\d{1,2})[\s._-]*(?:Episodes?|Epi|Ep|E)[\s._#-]*(\d{1,4})(?:v\d)?(?![A-Za-z0-9])"
    ),
    re.compile(r"(?i)(?<![A-Za-z0-9])(\d{1,2})x(\d{1,4})(?:v\d)?(?![A-Za-z0-9])"),
]
EPISODE_PATTERNS = [
    re.compile(r"(?i)(?<![A-Za-z0-9])(?:Episodes?|Epi|Ep|E)[\s._#-]*0*(\d{1,4})(?:v\d)?(?![A-Za-z0-9])"),
    re.compile(r"(?i)(?<![A-Za-z0-9])#\s*0*(\d{1,4})(?:v\d)?(?![A-Za-z0-9])"),
]
_SEPARATE_SEASON_PATTERN = re.compile(
    r"(?i)(?<![A-Za-z0-9])(?:Season[\s._-]*(\d{1,2})|S(\d{1,2}))(?![A-Za-z0-9])"
)

_HANDLE_PATTERN = re.compile(r"@[A-Za-z0-9_.]+")
_METADATA_TAG_PATTERN = re.compile(
    r"(?i)(?<![A-Za-z0-9])(?:"
    r"web[\s._-]*dl|web[\s._-]*rip|webrip|bluray|blu[\s._-]*ray|bdrip|hdrip|hdtv|"
    r"x264|x265|h[\s._-]?264|h[\s._-]?265|hevc|avc|av1|aac|ac3|eac3|ddp(?:5\.1)?|flac|opus|"
    r"10[\s._-]*bit|8[\s._-]*bit|"
    r"dual[\s._-]*audio|multi[\s._-]*audio|multi[\s._-]*sub|esub|esubs|msub|msubs|"
    r"(?:tamil|hindi|telugu|malayalam|kannada)(?:[\s._-]*(?:dub|dubbed|sub|subbed))?|"
    r"(?:english|eng|jap|jpn|japanese)[\s._-]*(?:dub|dubbed|sub|subbed)"
    r")(?![A-Za-z0-9])"
)
_BRACKET_METADATA_TOKEN = re.compile(
    r"(?i)(?<![A-Za-z0-9])(?:"
    r"web[\s._-]*dl|web[\s._-]*rip|webrip|bluray|blu[\s._-]*ray|bdrip|hdrip|hdtv|"
    r"x264|x265|h[\s._-]?264|h[\s._-]?265|hevc|avc|av1|aac|ac3|eac3|ddp(?:5\.1)?|flac|opus|"
    r"10[\s._-]*bit|8[\s._-]*bit|hdr(?:10)?|sdr|"
    r"dual[\s._-]*audio|multi[\s._-]*audio|multi[\s._-]*sub|multi|dual|"
    r"esub|esubs|msub|msubs|sub|subs|subbed|dub|dubbed|uncensored|raw|"
    r"tamil|tam|hindi|hin|telugu|tel|malayalam|mal|kannada|kan|"
    r"english|eng|japanese|jap|jpn|korean|kor|"
    r"2160p|1440p|1080p|720p|480p|360p|4k|2k|uhd"
    r")(?![A-Za-z0-9])"
)
_EMPTY_BRACKETS_PATTERN = re.compile(r"\[\s*[-+&/,._]*\s*\]|\(\s*[-+&/,._]*\s*\)")

QUALITY_ORDER = {
    "360p": 0,
    "480p": 1,
    "720p": 2,
    "1080p": 3,
    "1440p": 4,
    "2160p": 5,
}


@dataclass(frozen=True)
class ParsedMediaName:
    season: Optional[int]
    episode: Optional[int]
    quality: Optional[str]
    title: str


def split_filename(filename: str) -> Tuple[str, str]:
    name = os.path.basename(filename or "file")
    stem, extension = os.path.splitext(name)
    return stem, extension


def extract_quality(filename: str) -> Optional[str]:
    cleaned = _INVISIBLE_CHARS.sub("", filename or "")
    for pattern, quality in QUALITY_PATTERNS:
        if pattern.search(cleaned):
            return quality
    return None


def _episode_match(stem: str) -> Tuple[Optional[int], Optional[int], List[Tuple[int, int]]]:
    for pattern in SEASON_EPISODE_PATTERNS:
        match = pattern.search(stem)
        if match:
            return int(match.group(1)), int(match.group(2)), [match.span()]

    for pattern in EPISODE_PATTERNS:
        match = pattern.search(stem)
        if match:
            spans = [match.span()]
            masked = stem[:match.start()] + (" " * (match.end() - match.start())) + stem[match.end():]
            season_match = _SEPARATE_SEASON_PATTERN.search(masked)
            season = None
            if season_match:
                season = int(season_match.group(1) or season_match.group(2))
                spans.append(season_match.span())
            return season, int(match.group(1)), spans

    # Last numeric token is a conservative fallback for common releases such as
    # "Naruto - 012 - 1080p". Avoid resolution values and four-digit years.
    candidate_stem = re.sub(
        r"\[[^\]]*\]|\([^)]*\)",
        lambda match: " " * len(match.group()),
        stem,
    )
    for pattern, _quality in QUALITY_PATTERNS:
        candidate_stem = pattern.sub(lambda match: " " * len(match.group()), candidate_stem)
    tokens = list(re.finditer(r"(?<!\d)(\d{1,3})(?!\d)", candidate_stem))
    for match in reversed(tokens):
        before_ok = match.start() > 0 and candidate_stem[match.start() - 1] in " ._-"
        after_ok = match.end() == len(candidate_stem) or candidate_stem[match.end()] in " ._-"
        value = int(match.group(1))
        if before_ok and after_ok and 0 <= value <= 999:
            return None, value, [match.span()]
    return None, None, []


def _remove_release_brackets(text: str) -> str:
    """Remove likely release-group/hash/metadata brackets without deleting bracketed titles."""
    known_groups = {
        "subsplease", "erai-raws", "erai raws", "judas", "horriblesubs",
        "anime time", "animetime", "ember", "lostyears", "asw", "golumpa",
        "tsundere-raws", "toons hub", "toonshub", "toonworld4all",
    }

    def replace(match):
        content = match.group(1).strip()
        normalized = re.sub(r"\s+", " ", content).casefold()
        is_hash = bool(re.fullmatch(r"[A-Fa-f0-9]{6,}", content))
        is_short_release_code = bool(re.fullmatch(r"[A-Z0-9_-]{2,4}", content))
        is_known_group = normalized in known_groups
        is_site_tag = bool(re.search(r"(?i)(?:www\.|\.(?:com|net|org)\b)", content))
        is_empty = not content
        metadata_stripped = _BRACKET_METADATA_TOKEN.sub(" ", content)
        is_metadata_only = not re.search(r"[A-Za-z0-9]", metadata_stripped)
        if is_hash or is_short_release_code or is_known_group or is_site_tag or is_empty or is_metadata_only:
            return " "
        return match.group(0)

    text = re.sub(r"\[([^\]]*)\]", replace, text)
    text = _EMPTY_BRACKETS_PATTERN.sub(" ", text)
    return text


def parse_media_name(filename: str) -> ParsedMediaName:
    stem, _extension = split_filename(filename)
    stem = _INVISIBLE_CHARS.sub("", stem)
    season, episode, episode_spans = _episode_match(stem)
    quality = extract_quality(stem)

    title = stem
    for start, end in sorted(episode_spans, reverse=True):
        title = title[:start] + " " + title[end:]
    for pattern, _quality in QUALITY_PATTERNS:
        title = pattern.sub(" ", title)

    # Remove source handles before bracket cleanup so [@Channel] empties cleanly.
    title = _HANDLE_PATTERN.sub(" ", title)
    title = _remove_release_brackets(title)

    # Remove common release/language metadata without over-stripping real title words.
    title = _METADATA_TAG_PATTERN.sub(" ", title)
    title = re.sub(r"\[[^\]]*(?:www\.|\.com|\.net|\.org)[^\]]*\]", " ", title, flags=re.I)
    title = title.replace("(", " ").replace(")", " ")
    title = _EMPTY_BRACKETS_PATTERN.sub(" ", title)
    title = _SPACE_RUN.sub(" ", title).strip(" -_.[]()")
    return ParsedMediaName(season=season, episode=episode, quality=quality, title=title or "Unknown title")


def quality_sort_key(quality: Optional[str]):
    if not quality:
        return (99, "")
    return (QUALITY_ORDER.get(quality.lower(), 98), quality.lower())


def media_sort_key(parsed: ParsedMediaName, stable_index: int = 0):
    """Sort an already-parsed file by season, numeric episode, then quality."""
    return (
        parsed.season if parsed.season is not None else 0,
        parsed.episode if parsed.episode is not None else 10**9,
        quality_sort_key(parsed.quality),
        stable_index,
    )


def safe_filename(name: str, max_length: int = 180) -> str:
    """Strip path traversal/control characters while retaining a readable name."""
    name = os.path.basename(name or "file")
    stem, ext = os.path.splitext(name)
    stem = _INVALID_FILENAME_CHARS.sub(" ", stem)
    # Strict naming rule: never retain underscores in output filenames.
    stem = stem.replace("_", " ")
    stem = re.sub(r"\s+", " ", stem).strip(" .")
    if not stem:
        stem = "renamed_file"
    if stem.upper() in {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}:
        stem = f"_{stem}"
    remaining = max(1, max_length - len(ext))
    return f"{stem[:remaining]}{ext[:20]}"


def build_renamed_filename(template: str, original_filename: str) -> str:
    """Fill supported placeholders and preserve the layout written in the template."""
    parsed = parse_media_name(original_filename)
    values = {
        "season": f"{parsed.season:02d}" if parsed.season is not None else "XX",
        "episode": f"{parsed.episode:02d}" if parsed.episode is not None else "XX",
        "quality": parsed.quality or "Unknown",
        "title": parsed.title,
    }
    result = re.sub(
        r"\{(season|episode|quality|title)\}",
        lambda match: values[match.group(1).lower()],
        template,
        flags=re.I,
    )

    # Keep legacy plain-word placeholders working.
    legacy_season = values["season"]
    legacy_episode = values["episode"]
    result = re.sub(r"Sseason\b", f"S{legacy_season}", result, flags=re.I)
    result = re.sub(r"Eepisode\b", f"E{legacy_episode}", result, flags=re.I)
    result = re.sub(r"\bSeason\b", legacy_season, result)
    result = re.sub(r"\bEpisode\b", legacy_episode, result)
    result = re.sub(r"\bquality\b", parsed.quality or "Unknown", result)
    result = re.sub(r"\bQUALITY\b", parsed.quality or "Unknown", result)

    # Do not rewrite "S{season} Ep{episode}", bracketed quality, or custom
    # language labels. The configured template controls their exact layout.
    result = re.sub(r"\s+", " ", result).strip()

    _old_stem, extension = split_filename(original_filename)
    if extension and result.lower().endswith(extension.lower()):
        return safe_filename(result)
    return safe_filename(result + extension)
