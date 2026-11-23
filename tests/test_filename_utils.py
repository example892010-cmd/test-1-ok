import unittest

from helper.filename_utils import (
    build_renamed_filename,
    parse_media_name,
    media_sort_key,
    quality_sort_key,
    safe_filename,
)


class FilenameParserTests(unittest.TestCase):
    def test_common_episode_patterns(self):
        cases = {
            "[SubsPlease] Naruto - 01 (1080p) [ABC].mkv": (None, 1, "1080p", "Naruto"),
            "Naruto S02E03 720p.mkv": (2, 3, "720p", "Naruto"),
            "Naruto Season 1 Episode 12 480p.mkv": (1, 12, "480p", "Naruto"),
            "A Couple of Cuckoos S02 EP 08 [1080p].mkv": (2, 8, "1080p", "A Couple of Cuckoos"),
            "Naruto epi 2 1080p.mkv": (None, 2, "1080p", "Naruto"),
            "Naruto - 10 - 2160p.mkv": (None, 10, "2160p", "Naruto"),
            "[SubsPlease] Naruto - 01 (1080p) [ABC123].mkv": (None, 1, "1080p", "Naruto"),
            "86 Eighty-Six 1080p.mkv": (None, None, "1080p", "86 Eighty Six"),
        }
        for filename, expected in cases.items():
            with self.subTest(filename=filename):
                parsed = parse_media_name(filename)
                self.assertEqual(
                    (parsed.season, parsed.episode, parsed.quality, parsed.title),
                    expected,
                )

    def test_bracketed_title_and_year_are_preserved(self):
        bracketed = parse_media_name("[Oshi no Ko] Episode 01 1080p.mkv")
        year = parse_media_name("A Silent Voice (2016) 1080p.mkv")
        self.assertEqual(bracketed.title, "Oshi no Ko")
        self.assertEqual(year.title, "A Silent Voice 2016")

    def test_numeric_episode_sort_is_not_lexical(self):
        items = ["Episode 10 480p.mkv", "Episode 2 480p.mkv", "Episode 1 480p.mkv"]
        parsed = [parse_media_name(item) for item in items]
        self.assertEqual([item.episode for item in sorted(parsed, key=lambda item: item.episode)], [1, 2, 10])

    def test_episode_and_quality_order_for_batch_sort(self):
        names = [
            "Naruto Episode 02 1080p.mkv",
            "Naruto Episode 01 720p.mkv",
            "Naruto Episode 02 480p.mkv",
            "Naruto Episode 01 480p.mkv",
            "Naruto Episode 01 1080p.mkv",
            "Naruto Episode 02 720p.mkv",
        ]
        parsed = [parse_media_name(name) for name in names]
        ordered = sorted(
            parsed,
            key=lambda item: (item.episode if item.episode is not None else 10**9, quality_sort_key(item.quality)),
        )
        self.assertEqual(
            [(item.episode, item.quality) for item in ordered],
            [
                (1, "480p"), (1, "720p"), (1, "1080p"),
                (2, "480p"), (2, "720p"), (2, "1080p"),
            ],
        )

    def test_sort_key_orders_season_episode_quality_and_keeps_stability(self):
        names = [
            "Naruto S02E01 720p.mkv",
            "Naruto S01E02 480p.mkv",
            "Naruto S01E01 1080p.mkv",
            "Naruto S01E01 480p.mkv",
        ]
        parsed = [parse_media_name(name) for name in names]
        ordered = sorted(enumerate(parsed), key=lambda pair: media_sort_key(pair[1], pair[0]))
        self.assertEqual(
            [(item.season, item.episode, item.quality) for _, item in ordered],
            [(1, 1, "480p"), (1, 1, "1080p"), (1, 2, "480p"), (2, 1, "720p")],
        )

    def test_quality_order(self):
        qualities = ["1080p", "480p", "2160p", "720p", "1440p"]
        self.assertEqual(
            sorted(qualities, key=quality_sort_key),
            ["480p", "720p", "1080p", "1440p", "2160p"],
        )

    def test_template_keeps_original_extension(self):
        self.assertEqual(
            build_renamed_filename("Naruto S{season}E{episode} {quality}", "Naruto S01E02 1080p.MKV"),
            "Naruto S01E02 1080p.MKV",
        )

    def test_legacy_plain_word_template_tokens(self):
        self.assertEqual(
            build_renamed_filename("Naruto [Sseason Eepisode] - quality", "Naruto S02E03 1080p.mkv"),
            "Naruto [S02 E03] - 1080p.mkv",
        )
        self.assertEqual(
            build_renamed_filename("Season Episode QUALITY", "Naruto S02E03 1080p.mkv"),
            "02 03 1080p.mkv",
        )

    def test_tamil_source_tag_template_renames_to_clean_expected_format(self):
        original = "firefly’s Wedding - S01E04 [Tamil] 480p @Toonworld4all_Tamil.mkv"
        template = "@ANIFLIXANIMETAMIL - {title} S{season} Ep{episode} [{quality}] [ Tamil]"
        self.assertEqual(
            build_renamed_filename(template, original),
            "@ANIFLIXANIMETAMIL - firefly’s Wedding S01 Ep04 [480p] [ Tamil].mkv",
        )

    def test_template_does_not_drop_dotted_titles(self):
        self.assertEqual(
            build_renamed_filename("Dr. Stone S{season}E{episode} {quality}", "Dr. Stone S01E01 720p.mkv"),
            "Dr. Stone S01E01 720p.mkv",
        )

    def test_path_traversal_and_invalid_chars_are_removed(self):
        self.assertEqual(safe_filename("../../bad/name?.mkv"), "name.mkv")


if __name__ == "__main__":
    unittest.main()


def test_strict_removes_at_tags_and_underscores():
    original = "Firefly's Wedding - S01E04 [Tamil] 480p @Toonworld4all_Tamil.mkv"
    template = "@ANIFLIXANIMETAMIL - {title} S{season} Ep{episode} [{quality}] [ Tamil]"
    result = build_renamed_filename(template, original)
    assert result == "@ANIFLIXANIMETAMIL - Firefly's Wedding S01 Ep04 [480p] [ Tamil].mkv"
    assert "_" not in result
    assert "@Toonworld4all" not in result


def test_remove_at_tag_even_when_it_contains_underscores():
    parsed = parse_media_name("Anime S02E03 720p @source_name_extra.mkv")
    assert parsed.title == "Anime"
