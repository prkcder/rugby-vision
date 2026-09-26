# PR 008 - Self-Serve Project Documentation

## What I Built

A documentation entry point meant to let a technical user who is new to
computer vision understand and run the project on their own:

- **`README.md`** (previously empty): what the project is, what it
  demonstrates, the pipeline in one line, a minimal quick start, and links to
  the docs. It also states that the sample video is not committed.
- **`docs/getting-started.md`**: a step-by-step walkthrough, from
  prerequisites through to detection, tracking, evaluation and tests.
- **`docs/commands.md`**: a reference for every command, with its options
  (taken from the argparse definitions and `--help`) and example output.
- **`docs/how-it-works.md`**: the pipeline explained concept-first, then
  mapped to the tool and module responsible for each stage.

No code changed. Each file has a different job, and they link to each other
rather than repeating content.

Every documented command was run before being written down:

| Command | Result in this PR |
| --- | --- |
| Environment import check | `cv2 5.0.0 \| supervision 0.30.5` |
| `detection` (defaults) | Frame 545, 11 people, same confidences as the corrected PR 007 run |
| `detection --frame-index 200 --threshold 0.4 --output outputs/frame-200.jpg` | 15 people, image written |
| `detection --frame-index 5000` | `ValueError: frame_index 5000 is outside 0..1090` |
| `tracking` | 11442 person detections, 2123 unconfirmed, 44 IDs, the same counts as PR 005; loop 15.4 s, about 20 s total |
| `evaluation --csv outputs/evaluation/review.csv generate` | 20 reference + 60 annotated images, 60-row blank CSV |
| `evaluation generate` (default CSV) | Refused to overwrite `data/evaluation/review.csv` |
| `evaluation generate --csv ...` (wrong order) | `unrecognized arguments` |
| `evaluation summarize` (committed CSV) | Same table as PR 006 |
| `evaluation --csv outputs/evaluation/review.csv summarize` | 60 problems listed, no metrics |
| `pytest`, `pytest tests/test_tracking.py` | 25 passed; 4 passed |
| `ruff check src tests`, `ruff format --check src tests` | Pass |

All runs used the same CUDA GPU as earlier PRs.

## What I Learned

- **Writing run instructions exposed a fresh-clone trap.** The committed
  `data/evaluation/review.csv` is also `generate`'s default output path. Run
  as-is, `generate` refuses to overwrite it. Following the error message's
  hint (`--force`) would erase the completed manual review. The safe
  documented path writes the CSV under `outputs/` instead.
- **The position of a flag can matter.** `--csv` is defined on the top-level
  evaluation parser, not on the `generate`/`summarize` subparsers, so it has
  to come before the subcommand. Putting it after fails with
  `unrecognized arguments`.
- **The evaluation's sampled frames are fixed in code.** `select_frames()`
  divides frames 0–1023 (`GAMEPLAY_LAST_FRAME`) into 20 segments whatever
  the video. The last sampled frame is 998, so any video needs at least 999
  frames.
- **Re-running the pipeline reproduced earlier results.** Tracking gave
  exactly PR 005's detection, unconfirmed and ID counts. The generated CSV's
  machine-filled columns (frame, timestamp, threshold, detected count) match
  the committed review's exactly. Only the timing changed slightly
  (15.4 s vs 15.0 s).
- **Log noise is part of the first-run experience.** A normal run prints a
  `torch.jit.script` `FutureWarning`, two DINOv2 weight-loading warnings and
  an "optimize for inference" suggestion before any project output. A new
  user can't tell these are harmless, so the getting-started guide lists them.

## Important Terms

- **Self-serve documentation**: docs that let a user install, run and
  understand a project without help from its author.
- **Subcommand**: a command inside a command, like `generate` in
  `evaluation generate`, with its own options.
- **Top-level option**: an option that belongs to the main command and has
  to appear before the subcommand (`--csv` here).
- **Quick start**: the minimum steps to see the project work once.

## Problems I Hit

1. **`evaluation generate` fails on a fresh clone** because its default CSV
   path is the committed review.
2. **The first draft said the evaluation needs at least 1024 frames.** That
   assumed the sample covered all of 0–1023; the last sampled frame is
   actually 998.
3. **The first draft misdescribed the DINOv2 warning.** It said the message
   calls the behavior expected for a pretrained model. The actual text is
   "This is not a problem if finetuning a pretrained RF-DETR model".
4. **`ruff format --check .` still fails** on `docs/rf-oss-study-notes.md`
   (known since PR 003). A user running the obvious whole-repo command would
   see a failure unrelated to the Python code.
5. **Some first-run behavior couldn't be observed.** The RF-DETR weights
   were already cached, so the first-time download wasn't seen in this PR.
   CPU execution has never been run in this project.

## How I Solved Them

1. Kept this PR documentation-only. The docs give the safe command
   (`--csv outputs/evaluation/review.csv` before `generate`), show the
   refusal message and warn against `--force` on the committed file.
2. Read `select_frames()` and corrected the docs to 999 frames.
3. Replaced the paraphrase with the warning's actual text.
4. Documented the Ruff commands scoped to `src tests` and explained why.
5. Described the weight download as RF-DETR's general behavior and gave the
   cache path observed on this machine. The docs say the recorded runs used
   CUDA and that CPU execution and speed haven't been tested.

## What I Would Explain to a Customer

The repository now has a README that says what the project is and where to
go next, a step-by-step getting-started guide, a command reference, and a
plain-language explanation of the pipeline. Every command in the docs was run
as written, and the example outputs are real output from those runs.

Writing the docs as a first-time user would read them showed one real hazard:
the evaluation's default settings would try to write over the saved manual
review. The docs now steer people to a safe command. Changing the default is
left as a separate decision.

## Remaining Questions

- Should `evaluation generate` default to a CSV under `outputs/`, so a fresh
  clone can't collide with the committed review?
- Should `--csv` also be accepted after the subcommand?
- Should `GAMEPLAY_LAST_FRAME` become an option, or be derived from the video,
  so the evaluation works on other clips?
- What do first-run setup and CPU-only execution actually look like on a
  machine without cached weights or a GPU?
- `pyproject.toml` still has the placeholder description ("Add your
  description here") and `main.py` still prints a placeholder greeting.
  Should they be filled in or removed?
