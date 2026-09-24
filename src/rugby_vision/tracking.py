"""Full-video RF-DETR person detection with ByteTrack tracking.

Runs pretrained RF-DETR Nano on every frame, keeps "person" detections,
associates them across frames with ByteTrackTracker, and writes an annotated
video. Confirmed tracks are labelled with their tracker ID; detections the
tracker has not confirmed yet (tracker_id == -1) stay visible as "unconfirmed".
"""

import argparse
import time
from pathlib import Path

import cv2
import numpy as np
import supervision as sv
from tqdm import tqdm

from rugby_vision.detection import filter_people

UNCONFIRMED_ID = -1
UNCONFIRMED_COLOR = sv.Color.from_hex("#9e9e9e")


def is_confirmed(detections: sv.Detections) -> np.ndarray:
    """Boolean mask of detections that have a confirmed tracker ID."""
    if detections.tracker_id is None:
        return np.zeros(len(detections), dtype=bool)
    return detections.tracker_id != UNCONFIRMED_ID


def confirmed_tracks(detections: sv.Detections) -> sv.Detections:
    """Keep only detections with a confirmed tracker ID."""
    return detections[is_confirmed(detections)]


def build_track_labels(detections: sv.Detections) -> list[str]:
    """Labels like '#7 0.87', or 'unconfirmed 0.66' when there is no ID yet."""
    tracker_ids = (
        detections.tracker_id
        if detections.tracker_id is not None
        else np.full(len(detections), UNCONFIRMED_ID)
    )
    return [
        f"#{tracker_id} {confidence:.2f}"
        if tracker_id != UNCONFIRMED_ID
        else f"unconfirmed {confidence:.2f}"
        for tracker_id, confidence in zip(tracker_ids, detections.confidence)
    ]


class TrackAnnotator:
    """Draws confirmed tracks in per-ID colors and unconfirmed ones in gray."""

    def __init__(self) -> None:
        self.track_boxes = sv.BoxAnnotator(color_lookup=sv.ColorLookup.TRACK)
        self.track_labels = sv.LabelAnnotator(color_lookup=sv.ColorLookup.TRACK)
        self.unconfirmed_boxes = sv.BoxAnnotator(color=UNCONFIRMED_COLOR)
        self.unconfirmed_labels = sv.LabelAnnotator(color=UNCONFIRMED_COLOR)

    def annotate(self, image: np.ndarray, detections: sv.Detections) -> np.ndarray:
        confirmed_mask = is_confirmed(detections)
        scene = image.copy()
        for boxes, labels, subset in (
            (
                self.unconfirmed_boxes,
                self.unconfirmed_labels,
                detections[~confirmed_mask],
            ),
            (self.track_boxes, self.track_labels, detections[confirmed_mask]),
        ):
            scene = boxes.annotate(scene=scene, detections=subset)
            scene = labels.annotate(
                scene=scene, detections=subset, labels=build_track_labels(subset)
            )
        return scene


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, default=Path("data/raw/rugby.mp4"))
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument(
        "--output", type=Path, default=Path("outputs/tracked-rugby.mp4")
    )
    return parser.parse_args()


def main() -> None:
    # Imported here so the pure helpers above can be tested without loading torch.
    from rfdetr import RFDETRNano
    from trackers import ByteTrackTracker

    args = parse_args()
    video_info = sv.VideoInfo.from_video_path(str(args.video))

    model = RFDETRNano()
    # frame_rate scales ByteTrack's lost-track buffer to this video's real FPS.
    tracker = ByteTrackTracker(frame_rate=video_info.fps)
    annotator = TrackAnnotator()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    frames = sv.get_video_frames_generator(str(args.video))
    seen_ids: set[int] = set()
    frames_written = 0
    person_detections = 0
    unconfirmed_detections = 0

    start = time.perf_counter()
    with sv.VideoSink(str(args.output), video_info=video_info) as sink:
        for frame in tqdm(frames, total=video_info.total_frames, unit="frame"):
            # RF-DETR expects RGB; OpenCV gives BGR.
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            detections = model.predict(frame_rgb, threshold=args.threshold)
            tracked = tracker.update(filter_people(detections))

            confirmed = confirmed_tracks(tracked)
            seen_ids.update(confirmed.tracker_id.tolist())
            person_detections += len(tracked)
            unconfirmed_detections += len(tracked) - len(confirmed)

            sink.write_frame(annotator.annotate(frame, tracked))
            frames_written += 1
    elapsed = time.perf_counter() - start

    device = model.model.device
    print(f"Video:        {args.video}")
    print(
        f"Source:       {video_info.width}x{video_info.height}, "
        f"{video_info.fps:.2f} fps, {video_info.total_frames} frames"
    )
    print(f"Device:       {device}")
    print(f"Frames:       {frames_written} written")
    print(f"Time:         {elapsed:.1f}s ({frames_written / elapsed:.1f} frames/s)")
    print(
        f"Detections:   {person_detections} person, "
        f"{unconfirmed_detections} unconfirmed (tracker_id -1)"
    )
    print(f"Tracker IDs:  {len(seen_ids)} confirmed: {sorted(seen_ids)}")
    print(f"Output:       {args.output}")


if __name__ == "__main__":
    main()
