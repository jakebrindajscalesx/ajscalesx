import json
import tempfile
import unittest
from pathlib import Path

from clipping.manifest import Manifest, ManifestClip, write_manifest


class ManifestTest(unittest.TestCase):
    def test_write_manifest_produces_expected_json_shape(self):
        manifest = Manifest(
            source_video="https://example.com/video",
            clips=[
                ManifestClip(
                    file="clip_1.mp4",
                    start=412.3,
                    end=448.1,
                    score=14,
                    transcript="something happened",
                    suggested_caption="Something happened",
                    thumbnail="clip_1_thumb.jpg",
                )
            ],
        )

        with tempfile.TemporaryDirectory() as tmp:
            out_path = write_manifest(manifest, tmp)
            self.assertTrue(out_path.exists())
            with out_path.open() as f:
                data = json.load(f)

        self.assertEqual(data["source_video"], "https://example.com/video")
        self.assertEqual(len(data["clips"]), 1)
        clip = data["clips"][0]
        self.assertEqual(clip["file"], "clip_1.mp4")
        self.assertEqual(clip["start"], 412.3)
        self.assertEqual(clip["suggested_caption"], "Something happened")


if __name__ == "__main__":
    unittest.main()
