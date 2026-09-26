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
| [Commands](docs/commands.md) | Look up a command, its options and its output |
| [How it works](docs/how-it-works.md) | Understand the pipeline and what each tool is responsible for |
| [Learning notes](docs/learnings/) | Read what was built, observed and fixed in each change |

More concept and troubleshooting guides are planned.

## Scope

This project uses pretrained models only. It does not train models, detect the
ball, classify teams or identify individual players, and it has no web
interface or API.
