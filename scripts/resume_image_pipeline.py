"""Stitch resume screenshots and run tiled RapidOCR without printing resume text."""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
from pathlib import Path
from typing import Any

import cv2
import numpy as np


try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass


def output(**data: object) -> None:
    print(json.dumps(data, ensure_ascii=False, separators=(",", ":")))


def read_image(path: Path) -> np.ndarray:
    encoded = np.fromfile(str(path), dtype=np.uint8)
    image = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"image_unreadable:{path}")
    return image


def write_image(path: Path, image: np.ndarray) -> None:
    ok, encoded = cv2.imencode(path.suffix or ".png", image)
    if not ok:
        raise ValueError(f"image_encode_failed:{path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded.tofile(str(path))


def mask_fixed_back_arrow(image: np.ndarray) -> None:
    height, width = image.shape[:2]
    left_width = min(width, max(48, int(round(width * 0.10))))
    center_y = int(round(height * 0.50))
    half_height = max(40, int(round(height * 0.055)))
    top = max(0, center_y - half_height)
    bottom = min(height, center_y + half_height)
    image[top:bottom, 0:left_width] = 255


def stitch(args: argparse.Namespace) -> None:
    offsets = [int(value.strip()) for value in args.offsets.split(",") if value.strip()]
    if len(offsets) != len(args.pages):
        raise ValueError("offset_count_must_match_page_count")
    images = [read_image(path) for path in args.pages]
    if not images:
        raise ValueError("pages_required")
    width = images[0].shape[1]
    if any(image.shape[1] != width for image in images):
        raise ValueError("page_widths_differ")
    if not args.no_mask_left_arrow:
        for image in images:
            mask_fixed_back_arrow(image)

    height = max(offset + image.shape[0] for offset, image in zip(offsets, images))
    canvas = np.full((height, width, 3), 255, dtype=np.uint8)
    seams: list[dict[str, object]] = []
    for index, (offset, image) in enumerate(zip(offsets, images)):
        if index:
            previous_offset = offsets[index - 1]
            previous = images[index - 1]
            overlap = previous_offset + previous.shape[0] - offset
            if overlap > 0:
                previous_region = previous[
                    offset - previous_offset:previous.shape[0],
                    :,
                ]
                current_region = image[:overlap, :]
                difference = np.abs(
                    previous_region.astype(np.int16) - current_region.astype(np.int16)
                )
                seams.append(
                    {
                        "transition": f"{index}->{index + 1}",
                        "overlap_pixels": overlap,
                        "mean_abs_diff": round(float(difference.mean()), 3),
                        "p95_abs_diff": round(float(np.percentile(difference, 95)), 3),
                    }
                )
        canvas[offset:offset + image.shape[0], :] = image

    write_image(args.output, canvas)
    output(
        state="stitched",
        image=str(args.output.resolve()),
        width=int(width),
        height=int(height),
        page_count=len(images),
        offsets=offsets,
        seams=seams,
    )


def load_engine() -> tuple[object, str]:
    try:
        from rapidocr import RapidOCR

        return RapidOCR(), "rapidocr"
    except ImportError:
        try:
            from rapidocr_onnxruntime import RapidOCR

            return RapidOCR(), "rapidocr_onnxruntime"
        except ImportError as exc:
            raise RuntimeError(
                "RapidOCR is not installed; install the rapidocr package and onnxruntime"
            ) from exc


def normalize_result(result: Any) -> tuple[list[Any], list[str], list[float]]:
    if isinstance(result, tuple):
        result = result[0]
    if hasattr(result, "boxes") and hasattr(result, "txts"):
        boxes = list(result.boxes) if result.boxes is not None else []
        texts = list(result.txts) if result.txts is not None else []
        scores = list(result.scores) if getattr(result, "scores", None) is not None else []
        return boxes, [str(text) for text in texts], [float(score) for score in scores]
    if isinstance(result, list):
        boxes: list[Any] = []
        texts: list[str] = []
        scores: list[float] = []
        for item in result:
            if not isinstance(item, (list, tuple)) or len(item) < 2:
                continue
            boxes.append(item[0])
            texts.append(str(item[1]))
            scores.append(float(item[2]) if len(item) > 2 else 1.0)
        return boxes, texts, scores
    return [], [], []


def box_bounds(box: Any) -> tuple[float, float, float, float]:
    array = np.asarray(box, dtype=float).reshape(-1, 2)
    if array.size == 0:
        return 0.0, 0.0, 0.0, 0.0
    return (
        float(array[:, 0].min()),
        float(array[:, 1].min()),
        float(array[:, 0].max()),
        float(array[:, 1].max()),
    )


def normalized_text(value: str) -> str:
    return re.sub(r"\s+", "", value)


def rapidocr(args: argparse.Namespace) -> None:
    image = read_image(args.image)
    logging.disable(logging.INFO)
    engine, engine_name = load_engine()
    height, width = image.shape[:2]
    tile_height = max(256, args.tile_height)
    overlap = max(0, min(args.overlap, tile_height // 2))
    step = max(1, tile_height - overlap)
    starts = list(range(0, max(1, height - tile_height + 1), step))
    if not starts or starts[-1] + tile_height < height:
        starts.append(max(0, height - tile_height))
    starts = sorted(set(starts))

    all_lines: list[dict[str, object]] = []
    tile_metrics: list[dict[str, object]] = []
    total_started = time.perf_counter()
    for tile_index, start_y in enumerate(starts):
        end_y = min(height, start_y + tile_height)
        tile = image[start_y:end_y, :]
        started = time.perf_counter()
        raw_result = engine(tile)
        elapsed = time.perf_counter() - started
        boxes, texts, scores = normalize_result(raw_result)
        accepted = 0
        for raw_box, text, score in zip(boxes, texts, scores):
            text = text.strip()
            if not text:
                continue
            left, top, right, bottom = box_bounds(raw_box)
            if top < 3 or bottom > tile.shape[0] - 3:
                continue
            all_lines.append(
                {
                    "text": text,
                    "score": round(score, 6),
                    "box": [
                        round(left, 2),
                        round(start_y + top, 2),
                        round(right, 2),
                        round(start_y + bottom, 2),
                    ],
                    "absolute_y": round(start_y + top, 2),
                    "tile": tile_index,
                }
            )
            accepted += 1
        tile_metrics.append(
            {
                "index": tile_index,
                "top": start_y,
                "bottom": end_y,
                "elapsed_seconds": round(elapsed, 4),
                "accepted_lines": accepted,
            }
        )

    all_lines.sort(key=lambda line: (float(line["absolute_y"]), float(line["box"][0])))
    deduplicated: list[dict[str, object]] = []
    for line in all_lines:
        text_key = normalized_text(str(line["text"]))
        duplicate = None
        if text_key:
            for candidate in reversed(deduplicated[-100:]):
                if normalized_text(str(candidate["text"])) != text_key:
                    continue
                if abs(float(candidate["absolute_y"]) - float(line["absolute_y"])) <= 20:
                    duplicate = candidate
                    break
        if duplicate is not None:
            if float(line["score"]) > float(duplicate["score"]):
                duplicate.update(line)
            continue
        deduplicated.append(line)

    text = "\n".join(str(line["text"]) for line in deduplicated)
    args.text_output.parent.mkdir(parents=True, exist_ok=True)
    args.text_output.write_text(text + ("\n" if text else ""), encoding="utf-8")
    payload = {
        "state": "ok",
        "engine": engine_name,
        "image": str(args.image.resolve()),
        "width": int(width),
        "height": int(height),
        "tileHeight": tile_height,
        "overlap": overlap,
        "tileCount": len(starts),
        "elapsedSeconds": round(time.perf_counter() - total_started, 4),
        "rawLineCount": len(all_lines),
        "lineCount": len(deduplicated),
        "characterCount": len(text),
        "tiles": tile_metrics,
        "lines": deduplicated,
    }
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    output(
        state="ok",
        engine=engine_name,
        text_output=str(args.text_output.resolve()),
        json_output=str(args.json_output.resolve()),
        tile_count=len(starts),
        character_count=len(text),
        line_count=len(deduplicated),
        elapsed_seconds=payload["elapsedSeconds"],
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    stitch_parser = subparsers.add_parser("stitch")
    stitch_parser.add_argument("--pages", nargs="+", type=Path, required=True)
    stitch_parser.add_argument("--offsets", required=True)
    stitch_parser.add_argument("--output", type=Path, required=True)
    stitch_parser.add_argument("--no-mask-left-arrow", action="store_true")

    ocr_parser = subparsers.add_parser("rapidocr")
    ocr_parser.add_argument("--image", type=Path, required=True)
    ocr_parser.add_argument("--text-output", type=Path, required=True)
    ocr_parser.add_argument("--json-output", type=Path, required=True)
    ocr_parser.add_argument("--tile-height", type=int, default=1200)
    ocr_parser.add_argument("--overlap", type=int, default=150)

    args = parser.parse_args()
    try:
        if args.command == "stitch":
            stitch(args)
        else:
            rapidocr(args)
    except (OSError, RuntimeError, ValueError) as exc:
        output(state="error", reason=str(exc))
        sys.exit(2)


if __name__ == "__main__":
    main()
