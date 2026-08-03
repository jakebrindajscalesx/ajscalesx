import unittest

from clipping.scoring.base import ScoredSegment
from clipping.scoring.fusion import combine_scores


class CombineScoresTest(unittest.TestCase):
    def test_no_secondary_returns_primary_unchanged(self):
        primary = [ScoredSegment(start=0, end=10, text="a", score=5)]
        result = combine_scores(primary, None)
        self.assertEqual(result, primary)

    def test_overlapping_secondary_boosts_primary_score(self):
        primary = [ScoredSegment(start=0, end=10, text="a", score=5)]
        secondary = [ScoredSegment(start=5, end=15, text="", score=3, reasons=["chat_spike"])]
        result = combine_scores(primary, secondary, secondary_weight=2.0)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].score, 5 + 3 * 2.0)
        self.assertIn("chat_spike", result[0].reasons)

    def test_non_overlapping_secondary_kept_as_own_candidate(self):
        primary = [ScoredSegment(start=0, end=10, text="a", score=5)]
        secondary = [ScoredSegment(start=100, end=110, text="", score=4)]
        result = combine_scores(primary, secondary, secondary_weight=2.0)

        self.assertEqual(len(result), 2)
        boosted_primary = next(r for r in result if r.start == 0)
        secondary_only = next(r for r in result if r.start == 100)
        self.assertEqual(boosted_primary.score, 5)
        self.assertEqual(secondary_only.score, 4 * 2.0)


if __name__ == "__main__":
    unittest.main()
