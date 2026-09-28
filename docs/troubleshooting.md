# Troubleshooting

Checks to work through when Rugby Vision gives a result that looks wrong.
For what each kind of failure means and where it was observed, see
[Failure modes](failure-modes.md). For installation, video location and
first runs, see [Getting started](getting-started.md).

## Start by identifying which layer failed

A bad final result doesn't automatically mean the model failed. Work down
this list and stop at the first "yes":

```text
Are you looking at a different frame or moment than you meant?  → Input / media
Does the person have no box at all?                              → Detection
Is the box grey, labelled "unconfirmed"?                         → Tracking confirmation
Does the same person's ID change over time?                      → Tracking association (fragmentation)
Does one ID move onto a different person?                        → Tracking association (ID switch)
Do the metrics look wrong or contradict each other?              → Evaluation / review
```

The frame check comes first because every other diagnosis assumes you're
looking at the frame you think you are.

To look at one exact frame, run single-frame detection on it:

```bash
uv run python -m rugby_vision.detection --frame-index N
```

It decodes the video up to frame `N`, so the image it saves is exactly that
frame. The tracked video has no frame numbers drawn on it, and the time shown
in a video player won't exactly match `N / fps` on this clip (see
[I asked for a frame and got the wrong image](#i-asked-for-a-frame-and-got-the-wrong-image)).
Add `--threshold` and `--output` to compare settings (see
[Commands](commands.md#detection-one-frame)).

## A person is visible but has no box

No box at all, not even a grey one, means RF-DETR didn't return a `person`
box above the threshold. The tracker never saw this person.

Check in this order:

1. **Confirm you're looking at the exact frame.** Use
   `detection --frame-index N` as above, not a paused video player.
2. **Check the threshold in use.** The commands default to 0.5. The
   `Confidences:` line of the detection summary lists the score of every box
   that was kept.
3. **Check whether the person is a known hard case:** distant, cut off by the
   edge of the frame, partly hidden, or in a maul. Also check whether a
   neighbouring box covers them and someone else together; that's a merged
   box, not a separate miss.
4. **Compare a lower threshold on the same frame**, for example
   `--threshold 0.2`. If a box appears, the model did score the person, just
   below your threshold. If nothing appears even then, the detector isn't
   seeing them in this frame.
5. **Decide whether the miss matters for your application.** Some misses are
   the expected cost of a threshold chosen to avoid wrong boxes.

Lowering the threshold isn't a free fix. In the project's review, going from
0.40 to 0.20 cut missed people from 120 to 19, but raised wrong boxes from 3
to 92. See [There is no universally best threshold](detection.md#there-is-no-universally-best-threshold)
and [The confidence-threshold tradeoff](evaluation.md#the-confidence-threshold-tradeoff).

If boxes disappear only near the end of the project's clip, check the
picture first: from about frame 1025 a phone/YouTube player overlay covers
the match, and from frame 1073 there's nothing to detect (see
[Failure modes](failure-modes.md#12-the-source-stops-being-rugby-gameplay)).

## There are too many boxes

Check:

- **The threshold.** Low thresholds add boxes. At 0.20 the review found 92
  wrong boxes across 20 frames, against 3 at 0.40.
- **Duplicates.** Two boxes on one player, mostly in crowded frames at low
  thresholds.
- **Non-person objects.** Bags, a touch judge's flag and empty space were all
  boxed as `person` at 0.20. The person filter can't remove these; it only
  removes other classes.
- **Crowded overlap.** In a maul, many overlapping boxes may be a mix of
  separate players, duplicates and merged boxes. Look at the clean frame
  before deciding which is which.
- **Whether the "extra" boxes are really wrong.** Spectators, referees and
  touch judges are people. The model has no player class, so boxing them is
  correct.
- **Whether your application values recall over precision.** If missing a
  person costs more than an extra box, some extra boxes may be acceptable.

See [Failure modes 2–4](failure-modes.md#2-a-box-appears-on-something-that-isnt-a-person).

## A box is grey / unconfirmed

A grey box labelled `unconfirmed 0.66` means:

- RF-DETR **did** detect this person;
- ByteTrack returned the box without a confirmed track ID
  (`tracker_id == -1`).

That's not the same as "the detector missed them". The fix, if one is
needed, is on the tracking side.

Common reasons in this project: the track is new and hasn't been matched on
enough consecutive frames yet, or the box matched no existing track and
scored above RF-DETR's 0.5 but below the 0.7 that ByteTrack needs to start a
new one. The distant players on
the wide shot around frame 230 (0.51–0.65) stayed grey for that reason.

This project uses ByteTrack's default settings and hasn't tested changing
them. The exact rules and thresholds are in
[Confirmed and unconfirmed detections](tracking.md#confirmed-and-unconfirmed-detections).

## The tracker keeps creating new IDs

A person coming back under a new ID is **fragmentation**: the old track was
lost and a new one started.

Check what happened just before the new ID appeared:

- **A fast camera pan.** In the project's clip, a pan at frames 825–829 was
  followed by nine confirmed IDs ending (frames 824–860) and nine new ones,
  28–36, starting (frames 865–900). ByteTrack predicts movement from the
  boxes alone, so a pan makes everyone appear to jump.
- **Occlusion.** A player hidden in a maul may get no box for a while.
- **Leaving and re-entering the frame.** A track isn't kept forever; a lost
  track is kept for about one second of video.
- **Whether the detection disappeared between frames.** Step through the
  frames around the change. If the person had no box, or only a grey one, for
  a stretch, the track had nothing to continue on. The cause is then partly
  on the detection side.

Not every track breaks: `#22` stayed on the referee through the same pan,
because the referee kept being detected.

See [Fragmentation](tracking.md#fragmentation) and
[Why frame rate matters](tracking.md#why-frame-rate-matters).

## An ID jumps to another person

An ID moving from one person to another is an **ID switch**. It's an
association problem, not necessarily a detector problem.

The project's example, around frames 850–874:

1. `#22` is on the referee, and `#23` on a navy-shirted player running in
   front of him.
2. They overlap. `#23` stops being matched, and `#22`'s box stretches over
   both of them.
3. When they separate, `#22` continues on the navy player, and the referee
   comes back as a new ID, `#30`.

Both people were being detected. ByteTrack matches boxes by position and
motion, not by appearance, so when two boxes overlap it can't tell whose
track is whose.

Check whether the switch happened while two people overlapped, or while one
box covered both. If so, the cause is association during the overlap, not
a missing detection. See
[ID switches](tracking.md#id-switches) and the
[PR 005 learning note](learnings/PR-005-video-tracking.md).

## The result changes when I change the confidence threshold

That's expected. The threshold chooses which kind of mistake you'd rather
make. On the frames checked (25, 384, 742 and 793), lowering it only
**added** boxes; every box kept at a higher threshold was still there at a
lower one.

The project's manual review of 20 frames:

| Threshold | Precision | Recall | F1 |
| --- | --- | --- | --- |
| 0.20 | 0.796 | 0.950 | 0.866 |
| 0.40 | 0.989 | 0.683 | 0.808 |
| 0.60 | 1.000 (in this sample) | 0.447 | 0.618 |

- 0.20 found the most people and drew the most wrong boxes.
- 0.40 drew almost no wrong boxes and missed about a third of the people.
- 0.60 drew no wrong boxes **in this sample**, and missed more than half.

There's no universal best threshold. The highest F1 (0.20) doesn't make it
right for an application where a wrong box costs more than a missed person.
The commands' 0.5 default sits between two measured points and wasn't itself
reviewed. These numbers come from one clip and one reviewer.

See [Evaluation](evaluation.md#the-results) for how they were measured.

## I asked for a frame and got the wrong image

**Current behavior:** single-frame detection and the evaluation images both
decode the video in order up to the requested frame, so they return exactly
the frame you name. The tracking command processes every frame in order.

**Historical issue (fixed in PR 007):** earlier, single-frame detection
jumped straight to a frame with OpenCV's `CAP_PROP_POS_FRAMES` seek. On this
H.264 clip with a variable frame rate, that silently returned nearby frames:
asking for 545 returned 531, and seeking to frame 1075 or later failed. The
fix replaced the seek with sequential decoding.

If you see a mismatch now, check these first:

- **Frame numbers count from 0.** The summary's `Frame: 545 of 1091` means
  index 545 of frames 0–1090.
- **Seconds are approximate.** The time shown is `frame index / average fps`.
  On this variable-frame-rate clip, frame 545 is reported as 9.88s but its
  container timestamp is about 10.08s. The frame number is the exact
  reference; the seconds value isn't.
- **Your own code.** If you read frames with your own OpenCV seek, compare
  the result with a sequential decode before trusting it.

The full debugging story is in the
[PR 007 learning note](learnings/PR-007-exact-frame-reading.md).

## Evaluation numbers look inconsistent

Check:

1. **Recompute the arithmetic.** For every row, TP + FP must equal
   `detected_count`. For every frame, TP + FN must be the same at all three
   thresholds. `evaluation summarize` checks both and prints nothing if either
   fails.
2. **Check the ground truth.** Recount the people on the clean reference
   image (`frame-NNNN-reference.png`) rather than on an annotated one.
3. **Check the matching policy.** One box matches at most one person; one
   person is matched by at most one box. A box spanning two people is 1 TP +
   1 FN; two boxes on one person is 1 TP + 1 FP. See
   [The review policy](evaluation.md#the-review-policy).
4. **Compare the same boxes across thresholds.** On the frames checked, every
   box at a higher threshold was also drawn at the lower one. If a frame shows
   **fewer** TPs at a lower threshold, a box was probably judged differently
   in the two images.

Passing the checks in step 1 doesn't guarantee the review is consistent. They
prove each row adds up, not that the rows agree about the same boxes. That's
how three maul frames with fewer TPs at 0.20 than at 0.40 passed validation
until they were re-reviewed box by box in PR 009. See
[Why the policy must be consistent](evaluation.md#why-the-policy-must-be-consistent)
and the [PR 009 learning note](learnings/PR-009-evaluation-review-correction.md).

**Using another video:** detection, tracking and `evaluation generate` all
accept another video with `--video`. Evaluation generation, however, samples
20 fixed frame positions designed around the project's clip (frames 25 to
998, within its gameplay range 0–1023). Another video must have at least 999
frames, and those fixed positions may not land on useful gameplay moments in
it. See [Getting started](getting-started.md#generate-your-own-review-images).

## Warnings appear before model output

These messages were observed on every run that loads the model, and the runs
still completed normally:

| Message | Where it comes from |
| --- | --- |
| `FutureWarning: torch.jit.script is deprecated` | A dependency (PyTorch) |
| `File ... rf-detr-nano.pth already exists with correct MD5 hash.` | RF-DETR found its cached weights |
| Two `... not loading DINOv2 backbone weights. This is not a problem if finetuning a pretrained RF-DETR model.` | RF-DETR's backbone setup; the pretrained checkpoint still loads and detects normally |
| `Model is not optimized for inference. Latency may be higher than expected.` | A speed suggestion this project doesn't use |

That these didn't stop the recorded runs doesn't mean every warning is
harmless. A message not in this table, or any of these followed by missing
output, is worth investigating.

A real failure stops the command or produces no result. The ones observed in
this project:

| Output | Cause | Where it's explained |
| --- | --- | --- |
| `ValueError: frame_index ... is outside 0..1090` | `--frame-index` beyond the video | [Commands](commands.md#detection-one-frame) |
| `... refusing to overwrite a review. Pass --force to replace it.` | `generate` pointed at the committed review | [Commands](commands.md#evaluation-generate) (don't use `--force` on it) |
| `unrecognized arguments: --csv ...` | `--csv` placed after the subcommand | [Commands](commands.md#evaluation-generate) |
| `Review incomplete or inconsistent (...)` then `No metrics calculated.` | Blank or inconsistent review rows | [Commands](commands.md#evaluation-summarize) |
| `ruff format --check .` reports `docs/rf-oss-study-notes.md` | Ruff formats code blocks in Markdown | [Commands](commands.md#ruff) |

If the video can't be found or the environment won't import, go back to
[Getting started](getting-started.md).

## When reporting a problem

Collect:

- the exact command, including every option
- the video and frame number (not just the time in seconds)
- the RF-DETR threshold used
- a screenshot or the saved output image, and the terminal output
- what you expected to see
- what you actually saw
- which layer you think failed: detection, tracking, media or evaluation
- if tracker or model behavior matters, the package versions, from
  `uv pip list` (`uv.lock` pins `rfdetr` 1.10.1, `trackers` 2.6.0,
  `supervision` 0.30.5 and `opencv-python` 5.0.0.93)
