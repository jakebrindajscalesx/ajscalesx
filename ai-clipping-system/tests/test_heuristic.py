import unittest

from clipping.scoring.heuristic import TranscriptHeuristicScorer
from clipping.transcribe import Transcript, TranscriptSegment


def make_transcript(texts: list[str]) -> Transcript:
    segments = []
    t = 0.0
    for text in texts:
        segments.append(TranscriptSegment(text=text, start=t, end=t + 5, words=[]))
        t += 5
    return Transcript(segments=segments)


class TranscriptHeuristicScorerTest(unittest.TestCase):
    def setUp(self):
        self.scorer = TranscriptHeuristicScorer()

    def test_hook_keyword_scores_higher_than_plain_text(self):
        transcript = make_transcript(["this is completely normal filler text about nothing much"])
        plain_score = self.scorer.score(transcript)[0].score

        transcript = make_transcript(["you won't believe what happened next, it was insane"])
        hook_score = self.scorer.score(transcript)[0].score

        self.assertGreater(hook_score, plain_score)

    def test_exclamations_increase_score(self):
        base = make_transcript(["that happened"])
        excited = make_transcript(["that happened!!!"])
        self.assertGreater(
            self.scorer.score(excited)[0].score,
            self.scorer.score(base)[0].score,
        )

    def test_very_short_segment_is_penalized(self):
        transcript = make_transcript(["ok"])
        self.assertLess(self.scorer.score(transcript)[0].score, 0)

    def test_preserves_segment_timing(self):
        transcript = make_transcript(["hello there", "general kenobi"])
        scored = self.scorer.score(transcript)
        self.assertEqual(scored[0].start, 0.0)
        self.assertEqual(scored[1].start, 5.0)


if __name__ == "__main__":
    unittest.main()
