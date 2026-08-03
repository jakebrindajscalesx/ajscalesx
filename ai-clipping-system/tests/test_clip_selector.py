import unittest

from clipping.clip_selector import select_clips
from clipping.scoring.base import ScoredSegment


class SelectClipsTest(unittest.TestCase):
    def test_merges_nearby_high_scoring_segments(self):
        segments = [
            ScoredSegment(start=0, end=5, text="hello", score=3),
            ScoredSegment(start=6, end=10, text="world", score=4),
        ]
        clips = select_clips(segments, min_seconds=5, max_seconds=60, max_clips=10, merge_gap=4)
        self.assertEqual(len(clips), 1)
        self.assertEqual(clips[0].transcript, "hello world")
        self.assertEqual(clips[0].score, 7)

    def test_short_clip_padded_to_minimum_length(self):
        segments = [ScoredSegment(start=10, end=12, text="hi", score=5)]
        clips = select_clips(segments, min_seconds=15, max_seconds=60, max_clips=10)
        self.assertEqual(len(clips), 1)
        self.assertGreaterEqual(clips[0].duration, 15)

    def test_long_clip_trimmed_to_maximum_length(self):
        segments = [ScoredSegment(start=0, end=120, text="long", score=5)]
        clips = select_clips(segments, min_seconds=15, max_seconds=60, max_clips=10)
        self.assertLessEqual(clips[0].duration, 60)

    def test_negative_or_zero_score_segments_are_dropped(self):
        segments = [
            ScoredSegment(start=0, end=5, text="filler", score=0),
            ScoredSegment(start=100, end=105, text="good stuff", score=5),
        ]
        clips = select_clips(segments, min_seconds=5, max_seconds=60, max_clips=10)
        self.assertEqual(len(clips), 1)
        self.assertEqual(clips[0].transcript, "good stuff")

    def test_ranked_and_capped_at_max_clips(self):
        segments = [
            ScoredSegment(start=i * 100, end=i * 100 + 10, text=f"seg{i}", score=float(i))
            for i in range(1, 6)
        ]
        clips = select_clips(segments, min_seconds=5, max_seconds=60, max_clips=2)
        self.assertEqual(len(clips), 2)
        self.assertEqual(clips[0].transcript, "seg5")
        self.assertEqual(clips[1].transcript, "seg4")

    def test_overlapping_candidates_deduped_keeping_higher_score(self):
        # Far enough apart to not merge (gap > merge_gap), but padding both
        # out to min_seconds=20 makes them overlap heavily.
        segments = [
            ScoredSegment(start=0, end=2, text="high score", score=10),
            ScoredSegment(start=15, end=17, text="low score", score=5),
        ]
        clips = select_clips(segments, min_seconds=20, max_seconds=60, max_clips=10, merge_gap=4)
        self.assertEqual(len(clips), 1)
        self.assertEqual(clips[0].transcript, "high score")


if __name__ == "__main__":
    unittest.main()
