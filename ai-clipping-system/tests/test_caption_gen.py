import unittest

from clipping.caption_gen import suggest_caption


class SuggestCaptionTest(unittest.TestCase):
    def test_empty_transcript_falls_back(self):
        self.assertEqual(suggest_caption(""), "Watch this clip")

    def test_picks_short_complete_sentence(self):
        transcript = (
            "So anyway we were just walking around and honestly it was a pretty normal day. "
            "Then it happened. "
            "We could not believe our eyes at all after that moment."
        )
        caption = suggest_caption(transcript)
        self.assertEqual(caption, "Then it happened")

    def test_caption_capped_at_max_words(self):
        transcript = "word " * 20
        caption = suggest_caption(transcript)
        self.assertLessEqual(len(caption.split()), 10)

    def test_unknown_backend_falls_back_to_rule_based(self):
        caption = suggest_caption("Then it happened.", backend="claude")
        self.assertEqual(caption, "Then it happened")


if __name__ == "__main__":
    unittest.main()
