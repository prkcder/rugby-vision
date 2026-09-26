"""Manual RF-DETR person-detection review across confidence thresholds.

generate:  run RF-DETR Nano on 20 evenly spaced gameplay frames at several
           thresholds, save annotated images, and write a review CSV whose
           judgment columns are left blank for a human reviewer.
summarize: validate the completed review CSV and report precision, recall
           and F1 per threshold.

Manual matching rules for the reviewer:
- Each prediction can count as at most one true positive.
- Each real person can count as at most one true positive.
- One box covering two real people = 1 TP + 1 FN.
- Two boxes on one real person = 1 TP + 1 FP.
"""

import argparse
import csv
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from rugby_vision.detection import annotate, filter_people

# Frames 1024 onward show phone/YouTube player UI over the match (title bar and
# controls from ~1025, then the phone control centre from 1073), so they are
# not treated as normal gameplay.
GAMEPLAY_LAST_FRAME = 1023
SAMPLE_SIZE = 20
THRESHOLDS = (0.20, 0.40, 0.60)

COUNT_FIELDS = ("true_positives", "false_positives", "false_negatives")
MANUAL_FIELDS = (*COUNT_FIELDS, "occlusion_level", "notes")
MACHINE_FIELDS = ("frame_index", "timestamp_seconds", "threshold", "detected_count")
FIELDNAMES = (*MACHINE_FIELDS, *MANUAL_FIELDS)
OCCLUSION_LEVELS = ("low", "medium", "high")


def select_frames(last_frame: int, count: int = SAMPLE_SIZE) -> list[int]:
    """Midpoint of each of `count` equal segments of frames 0..last_frame."""
    total = last_frame + 1
    return [int((i + 0.5) * total / count) for i in range(count)]


def read_frames_sequentially(
    video_path: Path, indices: list[int]
) -> dict[int, np.ndarray]:
    """Read exact frames by decoding in order.

    OpenCV seeking (CAP_PROP_POS_FRAMES) on this MP4 lands on nearby keyframes
    rather than the requested frame, so seeking is avoided here.
    """
    wanted = set(indices)
    frames: dict[int, np.ndarray] = {}
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise FileNotFoundError(f"Could not open video: {video_path}")
    try:
        index = 0
        while len(frames) < len(wanted):
            ok, image = capture.read()
            if not ok:
                break
            if index in wanted:
                frames[index] = image
            index += 1
    finally:
        capture.release()
    missing = wanted - frames.keys()
    if missing:
        raise ValueError(f"Could not read frames: {sorted(missing)}")
    return frames


def add_caption(image: np.ndarray, text: str) -> np.ndarray:
    """Add a caption strip below the image so no frame pixels are covered."""
    captioned = cv2.copyMakeBorder(
        image, 0, 28, 0, 0, cv2.BORDER_CONSTANT, value=(0, 0, 0)
    )
    cv2.putText(
        captioned,
        text,
        (8, captioned.shape[0] - 9),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (255, 255, 255),
        1,
    )
    return captioned


def blank_review_row(
    frame_index: int, fps: float, threshold: float, detected_count: int
) -> dict[str, str]:
    """A CSV row with machine fields filled and every judgment field blank."""
    row = {field: "" for field in FIELDNAMES}
    row.update(
        frame_index=str(frame_index),
        timestamp_seconds=f"{frame_index / fps:.3f}",
        threshold=f"{threshold:.2f}",
        detected_count=str(detected_count),
    )
    return row


def write_review_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def read_review_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as file:
        return list(csv.DictReader(file))


def _parse_count(value: str | None) -> int | None:
    value = (value or "").strip()
    return int(value) if value.isdigit() else None


def validate_review(rows: list[dict[str, str]]) -> list[str]:
    """Return a list of problems; an empty list means the review is complete."""
    if not rows:
        return ["The review CSV has no rows."]

    errors: list[str] = []
    thresholds_by_frame: dict[str, list[str]] = defaultdict(list)
    ground_truth_by_frame: dict[str, set[int]] = defaultdict(set)

    for line, row in enumerate(rows, start=2):  # line 1 is the header
        where = f"line {line} (frame {row.get('frame_index')}, threshold {row.get('threshold')})"
        thresholds_by_frame[row.get("frame_index", "")].append(row.get("threshold", ""))

        counts = {field: _parse_count(row.get(field)) for field in COUNT_FIELDS}
        bad = [field for field, value in counts.items() if value is None]
        if bad:
            errors.append(f"{where}: {', '.join(bad)} must be whole numbers >= 0")

        occlusion = (row.get("occlusion_level") or "").strip()
        if occlusion and occlusion not in OCCLUSION_LEVELS:
            errors.append(
                f"{where}: occlusion_level must be one of {', '.join(OCCLUSION_LEVELS)}"
            )
        if bad:
            continue

        tp, fp, fn = (counts[field] for field in COUNT_FIELDS)
        detected = _parse_count(row.get("detected_count"))
        # Every drawn box is either a true or a false positive.
        if detected != tp + fp:
            errors.append(
                f"{where}: true_positives + false_positives = {tp + fp} "
                f"but detected_count = {row.get('detected_count')}"
            )
        ground_truth_by_frame[row.get("frame_index", "")].add(tp + fn)

    for frame, thresholds in thresholds_by_frame.items():
        if sorted(thresholds) != sorted(f"{t:.2f}" for t in THRESHOLDS):
            errors.append(
                f"frame {frame}: expected one row per threshold "
                f"{', '.join(f'{t:.2f}' for t in THRESHOLDS)}, found {', '.join(thresholds)}"
            )
    for frame, totals in ground_truth_by_frame.items():
        # Ground truth (TP + FN) cannot depend on the model's threshold.
        if len(totals) > 1:
            errors.append(
                f"frame {frame}: true_positives + false_negatives differs across "
                f"thresholds ({', '.join(map(str, sorted(totals)))})"
            )
    return errors


def _ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


@dataclass
class ThresholdMetrics:
    threshold: str
    frames: int
    true_positives: int
    false_positives: int
    false_negatives: int

    @property
    def precision(self) -> float | None:
        return _ratio(self.true_positives, self.true_positives + self.false_positives)

    @property
    def recall(self) -> float | None:
        return _ratio(self.true_positives, self.true_positives + self.false_negatives)

    @property
    def f1(self) -> float | None:
        precision, recall = self.precision, self.recall
        if precision is None or recall is None or precision + recall == 0:
            return None
        return 2 * precision * recall / (precision + recall)


def summarize_metrics(rows: list[dict[str, str]]) -> list[ThresholdMetrics]:
    """Sum TP/FP/FN over all frames per threshold (rows must be validated)."""
    totals: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0, 0])
    for row in rows:
        total = totals[row["threshold"]]
        total[0] += 1
        for i, field in enumerate(COUNT_FIELDS, start=1):
            total[i] += int(row[field])
    return [
        ThresholdMetrics(threshold, *values)
        for threshold, values in sorted(totals.items())
    ]


def _format(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.3f}"


def generate(video_path: Path, csv_path: Path, output_dir: Path, force: bool) -> None:
    from rfdetr import RFDETRNano

    if csv_path.exists() and not force:
        raise SystemExit(
            f"{csv_path} already exists; refusing to overwrite a review. "
            "Pass --force to replace it."
        )

    capture = cv2.VideoCapture(str(video_path))
    fps = capture.get(cv2.CAP_PROP_FPS)
    capture.release()

    indices = select_frames(GAMEPLAY_LAST_FRAME)
    frames = read_frames_sequentially(video_path, indices)
    model = RFDETRNano()
    output_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for frame_index in indices:
        frame = frames[frame_index]
        # Unannotated reference for the reviewer; PNG keeps every source pixel.
        reference = add_caption(
            frame, f"frame {frame_index} | {frame_index / fps:.2f}s | reference"
        )
        cv2.imwrite(
            str(output_dir / f"frame-{frame_index:04d}-reference.png"), reference
        )
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        for threshold in THRESHOLDS:
            people = filter_people(model.predict(frame_rgb, threshold=threshold))
            image = add_caption(
                annotate(frame, people),
                f"frame {frame_index} | {frame_index / fps:.2f}s | "
                f"threshold {threshold:.2f} | {len(people)} people",
            )
            name = f"frame-{frame_index:04d}-t{round(threshold * 100):03d}.jpg"
            cv2.imwrite(str(output_dir / name), image)
            rows.append(blank_review_row(frame_index, fps, threshold, len(people)))
            print(
                f"frame {frame_index:4d}  threshold {threshold:.2f}  {len(people):2d} people"
            )

    write_review_csv(csv_path, rows)
    print(
        f"Wrote {len(indices)} reference and {len(rows)} threshold images to "
        f"{output_dir}, and {len(rows)} rows to {csv_path}"
    )


def summarize(csv_path: Path) -> None:
    rows = read_review_csv(csv_path)
    errors = validate_review(rows)
    if errors:
        print(
            f"Review incomplete or inconsistent ({len(errors)} problems):",
            file=sys.stderr,
        )
        for error in errors:
            print(f"  {error}", file=sys.stderr)
        raise SystemExit("No metrics calculated.")

    print(
        f"{'threshold':>9} {'frames':>6} {'TP':>4} {'FP':>4} {'FN':>4} "
        f"{'precision':>9} {'recall':>7} {'F1':>6}"
    )
    for m in summarize_metrics(rows):
        print(
            f"{m.threshold:>9} {m.frames:>6} {m.true_positives:>4} "
            f"{m.false_positives:>4} {m.false_negatives:>4} "
            f"{_format(m.precision):>9} {_format(m.recall):>7} {_format(m.f1):>6}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--csv", type=Path, default=Path("data/evaluation/review.csv"))
    commands = parser.add_subparsers(dest="command", required=True)

    gen = commands.add_parser("generate", help="create images and a blank review CSV")
    gen.add_argument("--video", type=Path, default=Path("data/raw/rugby.mp4"))
    gen.add_argument("--output-dir", type=Path, default=Path("outputs/evaluation"))
    gen.add_argument("--force", action="store_true", help="overwrite an existing CSV")

    commands.add_parser("summarize", help="validate the review and print metrics")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == "generate":
        generate(args.video, args.csv, args.output_dir, args.force)
    else:
        summarize(args.csv)


if __name__ == "__main__":
    main()
