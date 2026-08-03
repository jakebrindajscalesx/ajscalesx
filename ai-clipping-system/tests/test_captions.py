import tempfile
import unittest
from pathlib import Path

from clipping.convert.captions import generate_ass_captions
from clipping.transcribe import Word


class GenerateAssCaptionsTest(unittest.TestCase):
    def test_writes_dialogue_lines_relative_to_clip_start(self):
        words = [
            Word(text="hello", start=100.0, end=100.3),
            Word(text="there", start=100.3, end=100.6),
            Word(text="friend", start=100.6, end=101.0),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "captions.ass"
            generate_ass_captions(words, clip_start=100.0, output_path=out_path)
            content = out_path.read_text()

        self.assertIn("[Events]", content)
        self.assertIn("HELLO THERE FRIEND", content)
        self.assertIn("Dialogue: 0,0:00:00.00,", content)

    def test_long_word_run_splits_into_multiple_chunks(self):
        words = [Word(text=str(i), start=float(i), end=float(i) + 0.5) for i in range(10)]
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "captions.ass"
            generate_ass_captions(words, clip_start=0.0, output_path=out_path)
            content = out_path.read_text()

        dialogue_lines = [l for l in content.splitlines() if l.startswith("Dialogue:")]
        self.assertGreater(len(dialogue_lines), 1)


if __name__ == "__main__":
    unittest.main()
