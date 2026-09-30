# Rugby Vision

Rugby Vision finds and follows people in rugby footage, running entirely on
your own machine. It uses a pretrained [RF-DETR](https://github.com/roboflow/rf-detr)
model to detect people, [ByteTrack](https://github.com/roboflow/trackers) to
follow them from frame to frame, and [Supervision](https://github.com/roboflow/supervision)
to draw the results.

It is a small, educational project: the goal is to show how these pieces fit
together on real sports footage, and where they struggle.

## What it demonstrates

- **Person detection** on a single frame with a pretrained RF-DETR model
- **Multi-object tracking** across a full video with ByteTrack
- **Video annotation** with boxes, confidence scores and tracker IDs
- **Model evaluation** by manual review at several confidence thresholds
- **Troubleshooting** written up as it happened, in the project's
  [learning notes](docs/learnings/)

## Pipeline

```text
video → frames → RF-DETR detection → keep people → ByteTrack tracking → annotated output
```

[How it works](docs/how-it-works.md) explains each step.

## Getting started

You need Python 3.11, [uv](https://docs.astral.sh/uv/) and a rugby video of
your own.

```bash
git clone https://github.com/prkcder/rugby-vision.git
cd rugby-vision
uv sync
# copy your clip to data/raw/rugby.mp4, then:
uv run python -m rugby_vision.detection
```

[Getting started](docs/getting-started.md) walks through the full setup.

> **The sample rugby video is not included in this repository.** Videos are
> gitignored. Provide your own clip at `data/raw/rugby.mp4`, or pass another
> path with `--video`.

## Documentation

| Document | Use it to |
| --- | --- |
| [Getting started](docs/getting-started.md) | Install, add a video and run each step for the first time |
| [Demo](docs/demo.md) | Walk through the project in 5–10 minutes for an audience |
| [Commands](docs/commands.md) | Look up a command, its options and its output |
| [How it works](docs/how-it-works.md) | Understand the pipeline and what each tool is responsible for |
| [Detection](docs/detection.md) | Learn what the detector outputs and how the confidence threshold trades misses for wrong boxes |
| [Tracking](docs/tracking.md) | Learn how tracker IDs are assigned and why they change |
| [Evaluation](docs/evaluation.md) | See how detection quality was measured and what the numbers mean |
| [Glossary](docs/glossary.md) | Look up a computer vision term |
| [Failure modes](docs/failure-modes.md) | Identify which part of the pipeline caused a bad result |
| [Troubleshooting](docs/troubleshooting.md) | Work through checks for a specific problem |
| [Hosted Roboflow](docs/hosted-roboflow.md) | See what changed when a one-class rugby-player model was trained, tested on an unseen match and published as a Workflow on Roboflow's hosted platform |
| [Learning notes](docs/learnings/README.md) | Read what was built, observed and fixed in each change |

## Scope

The local pipeline uses pretrained models only. It does not train models,
detect the ball, classify teams or identify individual players, and it has no
web interface or API. A separate
[hosted Roboflow experiment](docs/hosted-roboflow.md) fine-tuned a one-class
rugby-player model on Roboflow's platform; no training code is in this
repository.
