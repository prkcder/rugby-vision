# Learning Notes

Each note was written with the change it describes. Together they preserve
the project's implementation decisions, observations from the actual
footage, debugging discoveries, corrections and lessons learned. Later
corrections are documented explicitly while the current documentation is
kept accurate.

| PR | Topic | What changed / what was learned |
| --- | --- | --- |
| [003](PR-003-rfdetr-detection.md) | RF-DETR single-frame detection | Added single-frame person detection; learned that RF-DETR expects RGB, that `person` is class 1 not 0, and that model weights move to the GPU only on first `predict()`. |
| [005](PR-005-video-tracking.md) | Full-video tracking with ByteTrack | Added ByteTrack tracking with grey unconfirmed boxes, and traced most of the 44 IDs to a fast camera pan, an ID switch (`#22`) and players leaving and re-entering view. |
| [006](PR-006-detection-evaluation.md) | Manual detection evaluation | Added a manual review of 20 frames at three thresholds, showing the precision/recall tradeoff, and found that OpenCV frame seeking was inaccurate on this clip. |
| [007](PR-007-exact-frame-reading.md) | Exact frame reading | Replaced frame seeking with sequential decoding after PR 006 showed that PR 003's "frame 545" result came from about frame 531. |
| [008](PR-008-self-serve-docs.md) | Self-serve documentation | Added the README, getting started, commands and how-it-works docs; running every command found that `evaluation generate` targets the committed review by default. |
| [009](PR-009-evaluation-review-correction.md) | Evaluation review correction | Re-reviewed three maul frames box by box after finding their counts passed validation but disagreed across thresholds. |
| [010](PR-010-core-concepts.md) | Core concept guides | Added the detection, tracking, evaluation and glossary guides; checking their numbers against the review exposed the inconsistency corrected in PR 009. |
| [011](PR-011-troubleshooting-guides.md) | Failure modes and troubleshooting | Added guides that map each observed failure to the pipeline layer that owns it, with ordered checks per symptom. |
| [012](PR-012-demo-and-learning-index.md) | Demo guide and this index | Added a 5–10 minute presentation walkthrough and this index of the notes. |
| [013](PR-013-hosted-roboflow.md) | Hosted Roboflow experiment | Built a one-class rugby-player dataset with Auto Label and manual review, fine-tuned RF-DETR Small, tested it on an unseen match and fixed an invalid model ID in an Agent-built Workflow. |

PRs #1, #2 and #4 were project setup and repository-guideline changes and
have no learning note.

## Reading paths

- **Detection and evaluation:** 003 → 006 → 009
- **Tracking:** 005
- **Video and frame handling:** 007 (corrects 003)
- **Documentation:** 008 → 010 → 011 → 012
- **Hosted Roboflow:** 006 → 009 → 013 (the local threshold evaluation
  first; 013 meets the same tradeoff on an unseen match)
