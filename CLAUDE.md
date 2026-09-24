# Rugby Vision

## Goal

Build a small educational computer vision project using Roboflow's
open-source ecosystem.

The application processes rugby footage locally and demonstrates:

- person detection with RF-DETR
- multi-object tracking
- video annotation
- model evaluation
- troubleshooting/documentation

## Stack

Use:

- Python 3.11
- uv
- RF-DETR
- Supervision
- Roboflow Trackers
- OpenCV
- pytest
- ruff

## Scope

Keep this project intentionally small.

Do NOT add unless explicitly requested:

- web frontend
- API
- database
- authentication
- cloud deployment
- custom training
- ball detection
- tackle detection
- pass detection
- team classification
- player recognition
- jersey OCR

Prefer clear and simple Python.

## Roboflow OSS

The project uses:

- roboflow/rf-detr directly through the rfdetr package
- roboflow/supervision directly through the supervision package
- roboflow/trackers directly through the trackers package
- roboflow/notebooks as learning/reference material
- roboflow/sports as sports CV reference material

## Workflow

Before implementing any feature:

1. Explain the relevant CV concept in simple language.
2. Explain which files will change.
3. Implement the smallest working version.
4. Run it.
5. Run relevant tests/checks.
6. Explain any errors or unexpected behavior.
7. Update the current PR learning note.

Do not fabricate issues or observations.

## Learning Notes

For every PR create:

docs/learnings/PR-XXX-name.md

Use:

# PR XXX - Title

## What I Built

## What I Learned

## Important Terms

## Problems I Hit

## How I Solved Them

## What I Would Explain to a Customer

## Remaining Questions

Only document things we genuinely encountered.

## Git

Before committing, show me:

- files changed
- checks performed
- suggested commit message
- suggested PR title
- suggested PR description

Do not push or merge without my explicit instruction.