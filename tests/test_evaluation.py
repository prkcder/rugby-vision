import numpy as np
import pytest

from rugby_vision.evaluation import (
    MANUAL_FIELDS,
    ThresholdMetrics,
    add_caption,
    blank_review_row,
    read_review_csv,
    select_frames,
    summarize_metrics,
    validate_review,
    write_review_csv,
)

# All TP/FP/FN values below are synthetic test fixtures, not review results.


def reviewed_row(frame, threshold, detected, tp, fp, fn, occlusion=""):
    row = blank_review_row(frame, 50.0, threshold, detected)
    row.update(
        true_positives=str(tp),
        false_positives=str(fp),
        false_negatives=str(fn),
        occlusion_level=occlusion,
    )
    return row


def complete_review():
    # Two frames; ground truth (TP + FN) is 10 and 4 at every threshold.
    return [
        reviewed_row(100, 0.20, 12, 9, 3, 1),
        reviewed_row(100, 0.40, 9, 8, 1, 2),
        reviewed_row(100, 0.60, 6, 6, 0, 4, "high"),
        reviewed_row(200, 0.20, 5, 4, 1, 0),
        reviewed_row(200, 0.40, 4, 4, 0, 0),
        reviewed_row(200, 0.60, 3, 3, 0, 1, "low"),
    ]


def test_select_frames_uses_segment_midpoints():
    frames = select_frames(1023, count=20)

    assert len(frames) == 20
    assert frames[:3] == [25, 76, 128]
    assert frames[-1] == 998
    assert frames == select_frames(1023, count=20)


def test_caption_is_added_below_without_covering_the_frame():
    image = np.full((40, 60, 3), 255, dtype=np.uint8)

    captioned = add_caption(image, "frame 1")

    assert captioned.shape == (68, 60, 3)
    assert (captioned[:40] == 255).all()


def test_blank_row_leaves_every_judgment_field_empty():
    row = blank_review_row(128, 55.18, 0.4, 7)

    assert row["frame_index"] == "128"
    assert row["timestamp_seconds"] == "2.320"
    assert row["threshold"] == "0.40"
    assert row["detected_count"] == "7"
    assert all(row[field] == "" for field in MANUAL_FIELDS)


def test_csv_round_trip(tmp_path):
    path = tmp_path / "review.csv"
    rows = complete_review()

    write_review_csv(path, rows)

    assert read_review_csv(path) == rows


def test_blank_review_is_rejected():
    rows = [blank_review_row(100, 50.0, t, 3) for t in (0.2, 0.4, 0.6)]

    errors = validate_review(rows)

    assert len(errors) == 3
    assert all("must be whole numbers" in error for error in errors)


def test_complete_review_is_accepted():
    assert validate_review(complete_review()) == []


def test_non_numeric_and_negative_counts_are_rejected():
    rows = complete_review()
    rows[0]["true_positives"] = "nine"
    rows[1]["false_negatives"] = "-2"

    errors = validate_review(rows)

    assert len(errors) == 2


def test_tp_plus_fp_must_equal_detected_count():
    rows = complete_review()
    rows[0]["false_positives"] = "2"  # 9 + 2 != 12

    errors = validate_review(rows)

    assert any("detected_count = 12" in error for error in errors)


def test_ground_truth_must_match_across_thresholds():
    rows = complete_review()
    rows[1].update(true_positives="7", false_positives="2", false_negatives="2")

    errors = validate_review(rows)

    assert any("differs across thresholds" in error for error in errors)


def test_missing_threshold_row_is_rejected():
    errors = validate_review(complete_review()[:-1])

    assert any("frame 200: expected one row per threshold" in e for e in errors)


def test_unknown_occlusion_level_is_rejected():
    rows = complete_review()
    rows[0]["occlusion_level"] = "severe"

    errors = validate_review(rows)

    assert any("occlusion_level" in error for error in errors)


def test_summarize_metrics_sums_frames_per_threshold():
    metrics = {m.threshold: m for m in summarize_metrics(complete_review())}

    low = metrics["0.20"]
    assert (low.frames, low.true_positives, low.false_positives) == (2, 13, 4)
    assert low.false_negatives == 1
    assert low.precision == pytest.approx(13 / 17)
    assert low.recall == pytest.approx(13 / 14)
    assert metrics["0.60"].precision == 1.0
    assert metrics["0.60"].recall == pytest.approx(9 / 14)


def test_metrics_are_undefined_without_denominators():
    metrics = ThresholdMetrics("0.60", 1, 0, 0, 0)

    assert metrics.precision is None
    assert metrics.recall is None
    assert metrics.f1 is None


def test_f1_is_harmonic_mean():
    metrics = ThresholdMetrics("0.40", 1, 6, 2, 4)  # precision 0.75, recall 0.6

    assert metrics.f1 == pytest.approx(2 * 0.75 * 0.6 / 1.35)
