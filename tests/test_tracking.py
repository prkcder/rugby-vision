import numpy as np
import supervision as sv
from trackers import ByteTrackTracker

from rugby_vision.tracking import TrackAnnotator, build_track_labels, confirmed_tracks


def make_tracked(tracker_ids: list[int], confidences: list[float]) -> sv.Detections:
    count = len(tracker_ids)
    return sv.Detections(
        xyxy=np.tile(np.array([[10.0, 10.0, 50.0, 90.0]]), (count, 1)),
        confidence=np.array(confidences),
        class_id=np.ones(count, dtype=int),
        tracker_id=np.array(tracker_ids),
        data={"class_name": np.array(["person"] * count)},
    )


def test_confirmed_tracks_drops_unconfirmed_ids():
    tracked = make_tracked([3, -1, 7], [0.9, 0.66, 0.8])

    confirmed = confirmed_tracks(tracked)

    assert confirmed.tracker_id.tolist() == [3, 7]


def test_build_track_labels_never_shows_minus_one():
    tracked = make_tracked([7, -1], [0.871, 0.664])

    assert build_track_labels(tracked) == ["#7 0.87", "unconfirmed 0.66"]


def test_annotator_draws_unconfirmed_detections():
    image = np.zeros((100, 100, 3), dtype=np.uint8)

    annotated = TrackAnnotator().annotate(image, make_tracked([-1], [0.66]))

    # The unconfirmed box is still drawn, not dropped.
    assert annotated.any()
    assert not image.any()


def test_bytetrack_confirms_track_on_second_frame():
    # Follows the trackers 2.6.0 default minimum_consecutive_frames=2: a new
    # track reports tracker_id -1 on its first frame and gets a real ID once
    # it has been matched on 2 consecutive frames.
    tracker = ByteTrackTracker(frame_rate=30.0)
    detection = sv.Detections(
        xyxy=np.array([[100.0, 100.0, 150.0, 200.0]]),
        confidence=np.array([0.9]),
        class_id=np.array([1]),
    )

    first = tracker.update(detection)
    second = tracker.update(detection)
    third = tracker.update(detection)

    assert first.tracker_id.tolist() == [-1]
    assert second.tracker_id.tolist() == [0]
    assert third.tracker_id.tolist() == [0]
