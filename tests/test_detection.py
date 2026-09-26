import cv2
import numpy as np
import pytest
import supervision as sv

from rugby_vision.detection import build_labels, filter_people, read_frame


def make_detections(class_names: list[str], confidences: list[float]) -> sv.Detections:
    count = len(class_names)
    return sv.Detections(
        xyxy=np.tile(np.array([[10.0, 10.0, 50.0, 90.0]]), (count, 1)),
        confidence=np.array(confidences),
        # Pretrained RF-DETR uses sparse COCO category IDs, e.g. person = 1.
        class_id=np.arange(1, count + 1),
        data={"class_name": np.array(class_names)},
    )


def test_filter_people_keeps_only_person_class_names():
    detections = make_detections(
        ["person", "sports ball", "person", "chair"], [0.9, 0.8, 0.6, 0.7]
    )

    people = filter_people(detections)

    assert len(people) == 2
    assert list(people.data["class_name"]) == ["person", "person"]
    assert people.confidence.tolist() == [0.9, 0.6]


def test_filter_people_handles_no_people():
    people = filter_people(make_detections(["car"], [0.9]))

    assert len(people) == 0


def test_filter_people_requires_class_names():
    detections = sv.Detections(
        xyxy=np.array([[0.0, 0.0, 1.0, 1.0]]), class_id=np.array([1])
    )

    with pytest.raises(KeyError):
        filter_people(detections)


def test_build_labels_include_class_name_and_confidence():
    detections = make_detections(["person", "person"], [0.912, 0.5])

    assert build_labels(detections) == ["person 0.91", "person 0.50"]


def test_read_frame_defaults_to_middle_frame(tmp_path):
    # Each frame is a flat gray whose brightness encodes its index.
    video_path = tmp_path / "tiny.avi"
    writer = cv2.VideoWriter(
        str(video_path), cv2.VideoWriter_fourcc(*"MJPG"), 10, (32, 32)
    )
    for index in range(5):
        writer.write(np.full((32, 32, 3), index * 50, dtype=np.uint8))
    writer.release()

    frame = read_frame(video_path)

    assert frame.frame_count == 5
    assert frame.index == 2
    assert frame.seconds == pytest.approx(0.2)
    assert abs(float(frame.image.mean()) - 100) < 10


def test_read_frame_rejects_out_of_range_index(tmp_path):
    video_path = tmp_path / "tiny.avi"
    writer = cv2.VideoWriter(
        str(video_path), cv2.VideoWriter_fourcc(*"MJPG"), 10, (32, 32)
    )
    writer.write(np.zeros((32, 32, 3), dtype=np.uint8))
    writer.release()

    with pytest.raises(ValueError):
        read_frame(video_path, frame_index=5)


def test_read_frame_returns_requested_frame_pixels(tmp_path):
    # Each frame's gray level encodes its index, so pixels identify the frame.
    video_path = tmp_path / "tiny.avi"
    writer = cv2.VideoWriter(
        str(video_path), cv2.VideoWriter_fourcc(*"MJPG"), 10, (32, 32)
    )
    for index in range(20):
        writer.write(np.full((32, 32, 3), index * 12, dtype=np.uint8))
    writer.release()

    for requested in (0, 7, 13, 19):
        frame = read_frame(video_path, frame_index=requested)

        assert frame.index == requested
        assert abs(float(frame.image.mean()) - requested * 12) < 4
