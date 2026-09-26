# Commands

A reference for every command in the project. Run them from the repository
root. If you're setting up for the first time, start with
[Getting started](getting-started.md).

| Command | Purpose |
| --- | --- |
| [`rugby_vision.detection`](#detection-one-frame) | Detect people in one frame |
| [`rugby_vision.tracking`](#tracking-full-video) | Detect and track people through a whole video |
| [`rugby_vision.evaluation generate`](#evaluation-generate) | Create images and a blank CSV for manual review |
| [`rugby_vision.evaluation summarize`](#evaluation-summarize) | Check a completed review and print precision, recall and F1 |
| [`pytest`](#pytest) | Run the unit tests |
| [`ruff`](#ruff) | Lint and check formatting |

Every Python command accepts `--help`. The example outputs below come from the
project's own 832x384, 1091-frame clip on a CUDA GPU. Your numbers will
differ.

## Detection (one frame)

```bash
uv run python -m rugby_vision.detection
```

**What it does:** reads one frame, runs pretrained RF-DETR Nano on it, keeps
only `person` detections, draws a box and a `person 0.87`-style label on each,
and saves the image.

**Options:**

| Flag | Default | Meaning |
| --- | --- | --- |
| `--video` | `data/raw/rugby.mp4` | Video to read |
| `--frame-index` | the middle frame | Which frame to process, counting from 0 |
| `--threshold` | `0.5` | Minimum confidence a detection needs to be kept |
| `--output` | `outputs/detection-smoke-test.jpg` | Where to save the annotated image |

Example with options:

```bash
uv run python -m rugby_vision.detection --frame-index 200 --threshold 0.4 --output outputs/frame-200.jpg
```

A `--frame-index` outside the video's frame range stops with an error before
the model runs.

**Output:** the annotated image at `--output`, and a summary:

```text
Video:       data/raw/rugby.mp4
Frame:       545 of 1091 (9.88s at 55.18 fps)
Threshold:   0.5
Device:      cuda (NVIDIA GeForce RTX 4080 SUPER)
Detections:  11 total, classes: person
People:      11 retained
Confidences: 0.90, 0.88, 0.86, 0.86, 0.84, 0.80, 0.75, 0.73, 0.69, 0.64, 0.61
Output:      outputs/detection-smoke-test.jpg (832x384)
```

- `Detections` counts every class RF-DETR returned. `People` counts what is
  left after keeping only `person`.
- The seconds value is approximate for videos with a variable frame rate. The
  frame number is exact.

## Tracking (full video)

```bash
uv run python -m rugby_vision.tracking
```

**What it does:** runs RF-DETR on every frame, keeps `person` detections,
links them across frames with ByteTrack, and writes an annotated video.

**Options:**

| Flag | Default | Meaning |
| --- | --- | --- |
| `--video` | `data/raw/rugby.mp4` | Video to read |
| `--threshold` | `0.5` | RF-DETR's minimum confidence, applied before tracking |
| `--output` | `outputs/tracked-rugby.mp4` | Where to write the annotated video |

ByteTrack's own settings are the library defaults, except that the tracker is
told the video's real frame rate.

**Output:** the annotated video at `--output`, with the same resolution, frame
rate and frame count as the source. A progress bar shows while it runs, then a
summary:

```text
Video:        data/raw/rugby.mp4
Source:       832x384, 55.18 fps, 1091 frames
Device:       cuda
Frames:       1091 written
Time:         15.4s (70.8 frames/s)
Detections:   11442 person, 2123 unconfirmed (tracker_id -1)
Tracker IDs:  44 confirmed: [0, 1, 2, ..., 43]
Output:       outputs/tracked-rugby.mp4
```

- `Time` covers the frame loop only. Model loading adds a few seconds, and the
  whole command took about 20 seconds.
- `Detections` totals person boxes over all frames. `unconfirmed` counts the
  ones ByteTrack hadn't confirmed as a track, which are drawn in grey.
- `Tracker IDs` counts tracks, not people. One person can get several IDs
  over a clip (see [How it works](how-it-works.md#6-tracking-bytetrack)).

## Evaluation: generate

```bash
uv run python -m rugby_vision.evaluation \
  --csv outputs/evaluation/review.csv \
  generate
```

**What it does:** runs RF-DETR on 20 fixed, evenly spaced frames at
thresholds 0.20, 0.40 and 0.60, saves images for a person to review, and
writes a CSV whose review columns are blank.

**Options:**

| Flag | Where it goes | Default | Meaning |
| --- | --- | --- | --- |
| `--csv` | **before** `generate` | `data/evaluation/review.csv` | Where to write the review CSV |
| `--video` | after `generate` | `data/raw/rugby.mp4` | Video to read |
| `--output-dir` | after `generate` | `outputs/evaluation` | Where to save the images |
| `--force` | after `generate` | off | Overwrite an existing CSV |

`--csv` belongs to the evaluation command itself, not to the `generate`
subcommand, so its position matters:

```bash
# Works
uv run python -m rugby_vision.evaluation --csv outputs/evaluation/review.csv generate

# Fails: "unrecognized arguments: --csv outputs/evaluation/review.csv"
uv run python -m rugby_vision.evaluation generate --csv outputs/evaluation/review.csv
```

> **Don't run `generate` without `--csv` in a fresh clone.** The default path
> is the committed, completed review. `generate` refuses to overwrite it:
>
> ```text
> data/evaluation/review.csv already exists; refusing to overwrite a review. Pass --force to replace it.
> ```
>
> Adding `--force` would replace the manual review with blank rows.

**Output:**

- 20 reference images, `frame-NNNN-reference.png`, with no boxes and a
  frame/time caption underneath
- 60 annotated images, `frame-NNNN-tXXX.jpg` (for example
  `frame-0025-t020.jpg` for frame 25 at threshold 0.20), with a caption such as
  `frame 537 | 9.73s | threshold 0.40 | 11 people`
- the CSV, one row per frame and threshold:

```text
frame_index,timestamp_seconds,threshold,detected_count,true_positives,false_positives,false_negatives,occlusion_level,notes
25,0.453,0.20,33,,,,,
25,0.453,0.40,17,,,,,
```

The terminal prints one line per frame and threshold, then a summary:

```text
frame  998  threshold 0.60   5 people
Wrote 20 reference and 60 threshold images to outputs/evaluation, and 60 rows to outputs/evaluation/review.csv
```

The reviewer fills in `true_positives`, `false_positives`, `false_negatives`
and optionally `occlusion_level` (`low`, `medium` or `high`) and `notes`. The
review policy is described in the
[PR 006 learning note](learnings/PR-006-detection-evaluation.md).

## Evaluation: summarize

```bash
uv run python -m rugby_vision.evaluation summarize
```

**What it does:** checks the review CSV for missing or inconsistent entries.
If it is complete, it prints precision, recall and F1 for each threshold.
It doesn't read the video or load the model.

**Options:**

| Flag | Where it goes | Default | Meaning |
| --- | --- | --- | --- |
| `--csv` | **before** `summarize` | `data/evaluation/review.csv` | Review CSV to check |

**Output** for the committed review:

```text
threshold frames   TP   FP   FN precision  recall     F1
     0.20     20  342  109   36     0.758   0.905  0.825
     0.40     20  258    3  120     0.989   0.683  0.808
     0.60     20  169    0  209     1.000   0.447  0.618
```

If any row is incomplete or inconsistent, it lists every problem and prints no
metrics. For example, a freshly generated CSV gives:

```text
Review incomplete or inconsistent (60 problems):
  line 2 (frame 25, threshold 0.20): true_positives, false_positives, false_negatives must be whole numbers >= 0
  ...
No metrics calculated.
```

The checks:

- TP, FP and FN are whole numbers of 0 or more
- TP + FP equals `detected_count`
- TP + FN is the same for a frame at every threshold
- each frame has one row per threshold
- `occlusion_level`, if filled in, is `low`, `medium` or `high`

## pytest

```bash
uv run pytest
```

**What it does:** runs the unit tests in `tests/`. They use small generated
images, videos and detections, so they don't need the rugby video, the model
weights or a GPU.

**Useful options** (standard pytest flags):

- `-q` for shorter output
- `tests/test_tracking.py` to run one file

**Output:** a pass/fail summary, for example `25 passed in 0.77s`.

## Ruff

```bash
uv run ruff check src tests
uv run ruff format --check src tests
```

**What they do:**

- `ruff check` looks for lint problems such as unused imports and likely bugs.
- `ruff format --check` reports files whose formatting doesn't match Ruff's
  style, without changing them.

To apply formatting, drop `--check`: `uv run ruff format src tests`.

**Why limit them to `src tests`:** Ruff also formats Python code blocks inside
Markdown files. `ruff format --check .` reports `docs/rf-oss-study-notes.md`
as needing reformatting, so checking the whole repository fails even when all
Python code is correctly formatted.

**Output** when everything passes:

```text
All checks passed!
7 files already formatted
```
