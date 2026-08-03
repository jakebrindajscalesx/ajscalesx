import tempfile
import unittest
from pathlib import Path

from clipping.config import ConfigError, load_config

VALID_YAML = """
output_dir: clients
downloads_dir: downloads
state_file: state.json
sources:
  - client: acme
    platform: youtube
    channel: "https://www.youtube.com/@acme"
    max_clips_per_video: 5
  - client: acme
    platform: twitch
    channel: acme_channel
"""

MISSING_FIELD_YAML = """
sources:
  - client: acme
    platform: youtube
"""

BAD_PLATFORM_YAML = """
sources:
  - client: acme
    platform: instagram
    channel: acme
"""


class LoadConfigTest(unittest.TestCase):
    def _write(self, tmp_dir: str, content: str) -> Path:
        path = Path(tmp_dir) / "sources.yaml"
        path.write_text(content)
        return path

    def test_loads_valid_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(tmp, VALID_YAML)
            cfg = load_config(path)

        self.assertEqual(len(cfg.sources), 2)
        self.assertEqual(cfg.sources[0].platform, "youtube")
        self.assertEqual(cfg.sources[0].max_clips_per_video, 5)
        self.assertEqual(cfg.sources[1].max_clips_per_video, cfg.default_max_clips_per_video)

    def test_missing_channel_field_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(tmp, MISSING_FIELD_YAML)
            with self.assertRaises(ConfigError):
                load_config(path)

    def test_unsupported_platform_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(tmp, BAD_PLATFORM_YAML)
            with self.assertRaises(ConfigError):
                load_config(path)

    def test_missing_file_raises(self):
        with self.assertRaises(ConfigError):
            load_config("/nonexistent/sources.yaml")


if __name__ == "__main__":
    unittest.main()
