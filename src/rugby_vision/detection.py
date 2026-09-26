"""Single-frame RF-DETR person detection smoke test.

Reads one frame from a video, runs pretrained RF-DETR Nano on it, keeps only
"person" detections, draws them with Supervision, and saves the image.
"""

import argparse
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import supervision as sv

PERSON_CLASS_NAME = "person"


@dataclass
class Frame:
    image: np.ndarray  # BGR, as returned by OpenCV
    index: int
    fps: float
    frame_count: int

    @property
    def seconds(self) -> float:
        return self.index / self.fps if self.fps else 0.0


def read_frame(video_path: Path, frame_index: int | None = None) -> Frame:
    """Read the exact decoded frame at frame_index. Defaults to the middle frame.

    Frame.seconds is approximate: it divides by the reported (average) fps,
    which does not match the real timestamps of variable-frame-rate video.
    """
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise FileNotFoundError(f"Could not open video: {video_path}")
    try:
        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = capture.get(cv2.CAP_PROP_FPS)
        if frame_index is None:
            frame_index = frame_count // 2
        if not 0 <= frame_index < frame_count:
            raise ValueError(
                f"frame_index {frame_index} is outside 0..{frame_count - 1}"
            )
        # Decode forward from the start instead of seeking with
        # CAP_PROP_POS_FRAMES, which returned nearby frames on rugby.mp4.
        for _ in range(frame_index):
            if not capture.grab():
                raise RuntimeError(
                    f"Could not decode up to frame {frame_index} from {video_path}"
                )
        ok, image = capture.read()
        if not ok:
            raise RuntimeError(f"Could not read frame {frame_index} from {video_path}")
    finally:
        capture.release()
    return Frame(image=image, index=frame_index, fps=fps, frame_count=frame_count)


def filter_people(detections: sv.Detections) -> sv.Detections:
    """Keep only detections whose RF-DETR class name is "person"."""
    class_names = detections.data.get("class_name")
    if class_names is None:
        raise KeyError("Detections have no 'class_name' data to filter on")
    return detections[np.asarray(class_names) == PERSON_CLASS_NAME]


def build_labels(detections: sv.Detections) -> list[str]:
    """Build labels such as 'person 0.87' for each detection."""
    return [
        f"{class_name} {confidence:.2f}"
        for class_name, confidence in zip(
            detections.data["class_name"], detections.confidence
        )
    ]


def annotate(image: np.ndarray, detections: sv.Detections) -> np.ndarray:
    """Draw boxes and labels on a copy of the image."""
    annotated = sv.BoxAnnotator().annotate(scene=image.copy(), detections=detections)
    return sv.LabelAnnotator().annotate(
        scene=annotated, detections=detections, labels=build_labels(detections)
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, default=Path("data/raw/rugby.mp4"))
    parser.add_argument(
        "--frame-index",
        type=int,
        default=None,
        help="Frame to process (default: middle frame)",
    )
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument(
        "--output", type=Path, default=Path("outputs/detection-smoke-test.jpg")
    )
    return parser.parse_args()


def main() -> None:
    # Imported here so the pure helpers above can be tested without loading torch.
    import torch
    from rfdetr import RFDETRNano

    args = parse_args()
    frame = read_frame(args.video, args.frame_index)

    model = RFDETRNano()
    # RF-DETR expects RGB; OpenCV gives BGR.
    frame_rgb = cv2.cvtColor(frame.image, cv2.COLOR_BGR2RGB)
    detections = model.predict(frame_rgb, threshold=args.threshold)
    people = filter_people(detections)

    annotated = annotate(frame.image, people)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(args.output), annotated):
        raise RuntimeError(f"Could not write {args.output}")

    height, width = annotated.shape[:2]
    # RF-DETR moves weights to its device lazily, so read it after predict().
    device = model.model.device
    if device.type == "cuda":
        device = f"{device} ({torch.cuda.get_device_name(device)})"
    all_names = sorted(set(detections.data["class_name"]))
    print(f"Video:       {args.video}")
    print(
        f"Frame:       {frame.index} of {frame.frame_count} "
        f"({frame.seconds:.2f}s at {frame.fps:.2f} fps)"
    )
    print(f"Threshold:   {args.threshold}")
    print(f"Device:      {device}")
    print(f"Detections:  {len(detections)} total, classes: {', '.join(all_names)}")
    print(f"People:      {len(people)} retained")
    confidences = ", ".join(f"{c:.2f}" for c in sorted(people.confidence, reverse=True))
    print(f"Confidences: {confidences or 'none'}")
    print(f"Output:      {args.output} ({width}x{height})")


if __name__ == "__main__":
    main()
