"""Checks deterministic long-screenshot stitching."""

import contextlib
import io
import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

import numpy as np

import resume_image_pipeline


class ResumeImagePipelineTests(unittest.TestCase):
    def test_stitch_uses_offsets_and_reports_seams(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = np.full((12, 20, 3), 255, dtype=np.uint8)
            second = np.full((12, 20, 3), 255, dtype=np.uint8)
            first[9:12, :] = 80
            second[:3, :] = 80
            second[9:12, :] = 140
            first_path = root / "one.png"
            second_path = root / "two.png"
            output_path = root / "long.png"
            resume_image_pipeline.write_image(first_path, first)
            resume_image_pipeline.write_image(second_path, second)
            stream = io.StringIO()
            with contextlib.redirect_stdout(stream):
                resume_image_pipeline.stitch(
                    Namespace(
                        pages=[first_path, second_path],
                        offsets="0,9",
                        output=output_path,
                        no_mask_left_arrow=True,
                    )
                )
            result = json.loads(stream.getvalue())
            self.assertEqual(result["state"], "stitched")
            self.assertEqual(result["width"], 20)
            self.assertEqual(result["height"], 21)
            self.assertTrue(output_path.is_file())
            self.assertEqual(result["seams"][0]["overlap_pixels"], 3)

    def test_stitch_rejects_offset_count_mismatch(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            image_path = root / "one.png"
            resume_image_pipeline.write_image(
                image_path,
                np.full((10, 10, 3), 255, dtype=np.uint8),
            )
            with self.assertRaisesRegex(ValueError, "offset_count"):
                resume_image_pipeline.stitch(
                    Namespace(
                        pages=[image_path],
                        offsets="0,1",
                        output=root / "long.png",
                        no_mask_left_arrow=True,
                    )
                )


if __name__ == "__main__":
    unittest.main()
