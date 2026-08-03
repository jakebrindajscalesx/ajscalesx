import unittest

from clipping.convert.crop import TARGET_HEIGHT, TARGET_WIDTH, build_vertical_filter


class BuildVerticalFilterTest(unittest.TestCase):
    def test_widescreen_source_crops_width(self):
        filt = build_vertical_filter(1920, 1080, mode="center")
        self.assertIn("crop=", filt)
        self.assertIn(f"scale={TARGET_WIDTH}:{TARGET_HEIGHT}", filt)

    def test_offset_crop_stays_in_bounds(self):
        # x_center_frac near the edge should still produce a valid,
        # in-bounds crop rather than a negative x offset.
        filt = build_vertical_filter(1920, 1080, mode="face_track", x_center_frac=0.02)
        crop_part = filt.split(",")[0]
        _, dims = crop_part.split("=")
        _, _, x, _ = dims.split(":")
        self.assertGreaterEqual(int(x), 0)


if __name__ == "__main__":
    unittest.main()
