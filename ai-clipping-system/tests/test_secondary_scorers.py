import unittest

from clipping.scoring.twitch_chat import ChatEvent, TwitchChatSpikeScorer
from clipping.scoring.youtube_comments import Comment, YoutubeCommentVelocityScorer


class TwitchChatSpikeScorerTest(unittest.TestCase):
    def test_spike_window_scored_above_baseline(self):
        events = [ChatEvent(timestamp=t) for t in range(0, 100)]  # steady 1/sec baseline
        events += [ChatEvent(timestamp=50 + i * 0.1) for i in range(50)]  # spike at t=50-55

        scored = TwitchChatSpikeScorer(window_seconds=10).score(events)
        self.assertTrue(scored)
        spike_window = next(s for s in scored if s.start <= 50 < s.end)
        self.assertGreater(spike_window.score, 0)

    def test_no_events_returns_empty(self):
        self.assertEqual(TwitchChatSpikeScorer().score([]), [])


class YoutubeCommentVelocityScorerTest(unittest.TestCase):
    def test_extracts_timestamped_comment_window(self):
        comments = [Comment(text="2:14 this part killed me", like_count=50)]
        scored = YoutubeCommentVelocityScorer().score(comments)

        self.assertEqual(len(scored), 1)
        self.assertAlmostEqual(scored[0].start, 134 - 8)
        self.assertAlmostEqual(scored[0].end, 134 + 8)

    def test_comment_without_timestamp_is_ignored(self):
        comments = [Comment(text="great video no cap")]
        self.assertEqual(YoutubeCommentVelocityScorer().score(comments), [])


if __name__ == "__main__":
    unittest.main()
