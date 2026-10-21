"""Run from the repo root: python3 -m unittest discover tests"""
import sys, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import scrape

TEXT = (Path(__file__).parent / "fixtures" / "tango.txt").read_text()


def by_name(rows):
    return {r[0]: r for r in rows}


class ParseTests(unittest.TestCase):
    def setUp(self):
        self.rows = by_name(scrape.parse(TEXT))

    def test_reaction_line_does_not_hide_player(self):
        # A heart reaction sits between Sophie's name and time; the old parser read it as her name.
        self.assertEqual(self.rows["Sophie Evans"][1], 16)

    def test_emoji_badge_without_exclamation_is_not_a_name(self):
        # Wend shows "🍦 Sweet streak, daily treat." under "You"; the old parser took it as the name.
        rows = by_name(scrape.parse("Fran Example\n0:21\n16\nYou\n\n🍦 Sweet streak, daily treat.\n🍦 Sweet streak, daily treat.\n\n2:27"))
        self.assertEqual(rows["You"][1], 147)

    def test_streak_flame_still_works(self):
        self.assertEqual(self.rows["You"][1], 19)

    def test_trailing_space_in_name(self):
        self.assertEqual(self.rows["Oscar Gidley-Kitchin"][1], 17)

    def test_combined_no_hints_badge_means_no_hints(self):
        for n in ("Sophie Evans", "Oscar Gidley-Kitchin", "Lucie Day", "Sam Example"):
            self.assertFalse(self.rows[n][2], n)

    def test_plain_no_hints_badge(self):
        self.assertFalse(self.rows["Chris Fake"][2])

    def test_no_badge_or_only_mistakes_badge_means_hints(self):
        self.assertTrue(self.rows["Dana Nobadge"][2])
        self.assertTrue(self.rows["Eli Mistakesonly"][2])

    def test_unplayed_row_has_no_time(self):
        self.assertIsNone(self.rows["Quinn Unplayed"][1])

    def test_summary_card_does_not_override_first_row(self):
        # scroll_rows keeps the first row per name; the leaderboard row comes before the summary card.
        rows = scrape.parse(TEXT)
        first = {}
        for n, s, h, b in rows:
            first.setdefault(n, (s, h))
        self.assertEqual(first["You"], (19, False))

    def test_time_without_a_name_is_an_error(self):
        with self.assertRaises(ValueError):
            scrape.parse("🔥\n1\n0:19\n")


class CompletenessTests(unittest.TestCase):
    def test_passes_when_everyone_parsed(self):
        scrape.check_complete(TEXT, scrape.parse(TEXT))

    def test_fails_when_a_tracked_player_is_dropped(self):
        rows = [r for r in scrape.parse(TEXT) if r[0] != "Sophie Evans"]
        with self.assertRaisesRegex(ValueError, "Sophie Evans"):
            scrape.check_complete(TEXT, rows)


if __name__ == "__main__":
    unittest.main()
