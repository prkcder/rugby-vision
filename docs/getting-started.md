# Getting Started

This guide takes you from a fresh clone to a tracked rugby video. Each step
builds on the previous one, so work through them in order the first time.

For every option of every command, see [Commands](commands.md). For what the
pipeline is doing and why, see [How it works](how-it-works.md).

## 1. Prerequisites

- **Python 3.11.** The repository pins it in `.python-version`.
- **[uv](https://docs.astral.sh/uv/)**, which installs Python packages and
  runs the project's commands. The project was set up with uv 0.9.10.
- **git**, to clone the repository.
- **An internet connection on the first run**, so RF-DETR can download its
  model weights (see [First-run notes](#first-run-notes)).
- **A rugby video of your own.** None is included.

**GPU:** every recorded run of this project used an NVIDIA GPU through CUDA.
The code does not require a GPU, but CPU execution and CPU speed have not been
tested or measured in this repository.

## 2. Clone the repository

```bash
git clone https://github.com/prkcder/rugby-vision.git
cd rugby-vision
```

All commands in these docs are run from the repository root.

## 3. Install

```bash
uv sync
```

This creates a virtual environment in `.venv/`, installs the exact versions
pinned in `uv.lock` (RF-DETR, Supervision, Trackers, OpenCV and their
dependencies, plus pytest and Ruff for development), and installs the
`rugby_vision` package itself so it can be run with `python -m`.

You don't need to activate the environment. Prefixing a command with
`uv run` runs it inside `.venv/`.

## 4. Add your video

The commands look for the video at:

```text
data/raw/rugby.mp4
```

Copy your clip there. The relevant folders are:

| Folder | Contents | Committed to git? |
| --- | --- | --- |
| `data/raw/` | Your source video | No, videos are gitignored |
| `data/evaluation/` | The completed manual review, `review.csv` | Yes |
| `outputs/` | Everything the commands produce | No, gitignored |

To use a video somewhere else, pass `--video path/to/clip.mp4` to any command
that reads video.

## 5. Check the environment

```bash
uv run python -c "import cv2, rfdetr, supervision, trackers; print('cv2', cv2.__version__, '| supervision', supervision.__version__)"
```

If all four libraries import, it prints their versions, for example:

```text
cv2 5.0.0 | supervision 0.30.5
```

A `FutureWarning` about `torch.jit.script` may appear first. It comes from a
dependency and can be ignored.

## 6. Detect people in one frame

```bash
uv run python -m rugby_vision.detection
```

This reads the middle frame of the video, runs RF-DETR on it, keeps only the
`person` detections and saves an annotated image. The terminal shows a
summary like this (from the project's own clip):

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

Open `outputs/detection-smoke-test.jpg` to see a box and a `person 0.87`-style
label on each detection. Your numbers will differ with a different video.

This is the quickest way to confirm the video, the model and your hardware
work together.

## 7. Track people through the whole video

```bash
uv run python -m rugby_vision.tracking
```

This runs detection on every frame, links the detections over time with
ByteTrack, and writes `outputs/tracked-rugby.mp4`. A progress bar shows while
it runs. On the project's 1091-frame clip it took about 20 seconds in total on
the GPU.

In the output video:

- **Coloured boxes labelled `#7 0.87`** are confirmed tracks. The number is
  the tracker ID and the decimal is RF-DETR's confidence.
- **Grey boxes labelled `unconfirmed 0.66`** are people RF-DETR found but
  ByteTrack hasn't confirmed as a track yet.

A tracker ID is not a player's identity. The same person can receive a new ID
after being hidden or after a fast camera pan.
[How it works](how-it-works.md#6-tracking-bytetrack) explains why.

## 8. Evaluation material

The evaluation compares RF-DETR's detections with a person's manual count on
20 sampled frames, at confidence thresholds 0.20, 0.40 and 0.60.

### See the results of the committed review

The completed review is committed, so this works without a video:

```bash
uv run python -m rugby_vision.evaluation summarize
```

```text
threshold frames   TP   FP   FN precision  recall     F1
     0.20     20  342  109   36     0.758   0.905  0.825
     0.40     20  258    3  120     0.989   0.683  0.808
     0.60     20  169    0  209     1.000   0.447  0.618
```

TP, FP and FN are the reviewer's counts of correct boxes, wrong boxes and
missed people. The
[PR 006 learning note](learnings/PR-006-detection-evaluation.md) explains
how the review was done and what the numbers mean.

### Generate your own review images

```bash
uv run python -m rugby_vision.evaluation \
  --csv outputs/evaluation/review.csv \
  generate
```

This saves, under `outputs/evaluation/`:

- 20 unannotated reference images (`frame-0025-reference.png`, ...)
- 60 annotated images, one per frame and threshold (`frame-0025-t020.jpg`, ...)
- a new `review.csv` with the review columns left blank for you to fill in

**Two things to know:**

- **Always pass `--csv` with a path under `outputs/`.** Without it, `generate`
  targets the committed `data/evaluation/review.csv` and stops with
  `refusing to overwrite a review`. Adding `--force` there would erase the
  completed manual review.
- **`--csv` must come before `generate`.** It is an option of the evaluation
  command, not of the subcommand, so
  `evaluation generate --csv ...` fails with `unrecognized arguments`.

The 20 frames are sampled evenly from frames 0–1023, which are the gameplay
frames in the project's own clip (frames 25, 76, 128, ... up to 998). The
positions are fixed in the code, so with a different video they stay the same
and the video needs at least 999 frames.

## 9. Run the tests and linter

```bash
uv run pytest
uv run ruff check src tests
uv run ruff format --check src tests
```

The tests use small generated images and videos, so they don't need the rugby
video, the model weights or a GPU. Keep the Ruff commands limited to `src` and
`tests` (see [Commands](commands.md#ruff) for why).

## First-run notes

- **Model weights.** On first use, RF-DETR downloads the pretrained Nano
  checkpoint and caches it locally. On the machine used for this project the
  cached file is `~/.roboflow/models/rf-detr-nano.pth`. Later runs log
  `already exists with correct MD5 hash` and skip the download.
- **Harmless log messages.** Each run that loads the model prints warnings
  that don't stop it:
  - two `not loading DINOv2 backbone weights` warnings. The message itself
    says this "is not a problem if finetuning a pretrained RF-DETR model", and
    the pretrained checkpoint still loads and detects normally.
  - `Model is not optimized for inference`, a speed suggestion this project
    doesn't use
  - a `torch.jit.script` `FutureWarning` from a dependency
- **Outputs are overwritten.** Running a command again replaces its previous
  output files in `outputs/`.

## Next steps

- [Commands](commands.md): every option and output
- [How it works](how-it-works.md): what each stage does
- [Learning notes](learnings/): what was observed and fixed during development
