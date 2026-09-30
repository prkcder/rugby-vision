# Demo

A 5–10 minute walkthrough for presenting Rugby Vision in an interview, a
technical conversation or a customer explanation. It's a checklist of what to
run and what to point out, not a script to memorize.

The step timings are rough presentation guidance, not measured runtimes.

## What this project does

Rugby Vision finds and follows people in rugby footage, on your own machine:

- **RF-DETR Nano**, a pretrained model, detects people in each frame.
- **Supervision** holds the detections in one shared format, draws boxes and
  labels, and reads and writes video.
- **ByteTrack**, from Roboflow's `trackers` package, links detections across
  frames and assigns tracker IDs.
- **A manual review** of 20 frames measures how well the detector finds
  people at three confidence thresholds.

Be clear about scope:

- It detects **people**, not rugby roles. Players, referees and spectators
  are all `person`.
- **Tracker IDs are not player identities.**
- It doesn't detect the ball.
- The local pipeline doesn't train or fine-tune a model; it uses pretrained
  weights as-is. (A separate hosted experiment did; see
  [below](#optional-hosted-roboflow-extension-23-min).)
- Everything runs locally.
- The sample rugby video isn't in the repository.

## Before the demo

Set up with [Getting started](getting-started.md). Then:

- Put a rugby video at `data/raw/rugby.mp4`, or pass `--video path/to/clip.mp4`
  to the detection and tracking commands.
- Run the detection command once beforehand. The first run may download the
  model weights.
- Run the tracking command beforehand too, so the annotated video is ready to
  play. The project's recorded runs used a CUDA GPU, where the whole clip
  took about 20 seconds; CPU speed hasn't been tested.
- Expect a few warnings before the model output. They're listed in
  [Troubleshooting](troubleshooting.md#warnings-appear-before-model-output).

## 1. Show single-frame detection (~1–2 min)

```bash
uv run python -m rugby_vision.detection
```

Point out:

- **The exact frame.** The `Frame:` line names the frame that was analysed.
  By default it's the middle frame of the video.
- **Person boxes** in `outputs/detection-smoke-test.jpg`, each labelled like
  `person 0.87`.
- **Confidence values.** The `Confidences:` line lists the score of every
  box kept at the 0.5 default threshold.
- **The generic `person` class.** The model was trained on COCO's everyday
  photos, not rugby. It has no player, referee or ball-carrier class.

Optionally, show a specific frame:

```bash
uv run python -m rugby_vision.detection --frame-index 545
```

Frame 545 is the middle of the project's own clip. On another video, choose
a frame worth showing from that video.

## 2. Show full-video tracking (~2 min)

```bash
uv run python -m rugby_vision.tracking
```

Explain while the video plays (`outputs/tracked-rugby.mp4`):

- RF-DETR runs on **every frame on its own**; it remembers nothing between
  frames.
- ByteTrack **associates** each frame's boxes with the tracks it's already
  following, using position and motion only.
- **Coloured boxes labelled `#7 0.87`** are confirmed tracks: tracker ID,
  then RF-DETR's confidence.
- **Grey boxes labelled `unconfirmed`** are people RF-DETR found but
  ByteTrack hasn't confirmed as a track.
- **An ID is a track, not an identity.** The summary's `Tracker IDs` line
  counts tracks, not people.

What happened on the project's clip:

- **Fragmentation after a fast pan.** After a pan at frames 825–829, nine
  IDs ended and nine new ones started as players came back into view.
- **An ID switch.** `#22` moved from the referee to a navy-shirted player
  when they overlapped, and the referee came back as `#30`.
- **Dense overlap.** Rucks and tackles produce heavily overlapping boxes,
  and sometimes one box on two players.

Details: [Tracking](tracking.md#when-tracks-go-wrong) and
[Failure modes](failure-modes.md#tracking).

## 3. Show evaluation (~2 min)

```bash
uv run python -m rugby_vision.evaluation summarize
```

This reads the committed manual review, so it works without a video:

```text
threshold frames   TP   FP   FN precision  recall     F1
     0.20     20  359   92   19     0.796   0.950  0.866
     0.40     20  258    3  120     0.989   0.683  0.808
     0.60     20  169    0  209     1.000   0.447  0.618
```

- **TP** are boxes on real people, **FP** wrong boxes, **FN** missed people,
  all counted by a reviewer on 20 frames.
- **The key lesson:** the lower threshold found more people but also drew
  more wrong boxes. There's no universally best threshold; the right one
  depends on whether a missed person or a wrong box costs more.
- The 0 false positives at 0.60 were in this sample only.

Writing the concept docs exposed an inconsistency in the manual review on
three maul frames. It was re-reviewed and corrected in PR 9, and these are
the corrected numbers. See the
[PR 009 learning note](learnings/PR-009-evaluation-review-correction.md).

## 4. Show one failure mode (~1–2 min)

The point: **a bad final result doesn't automatically mean the detector
failed.** Pick one:

- **A. Grey / unconfirmed box.** Find a grey box in the tracked video. The
  detector found the person; the tracker hadn't confirmed a track. Missing
  box and grey box belong to different layers.
- **B. Fragmentation after camera motion.** Find a fast pan and watch the
  IDs. A real person can come back with a new tracker ID because ByteTrack
  predicts motion from boxes alone.
- **C. ID switch.** Find two players crossing. An ID can move from one
  person to the other because ByteTrack doesn't know what anyone looks like.

On the project's clip, the pan at frames 825–829 shows B, and frames
850–874 show C. On another video, look for the same kinds of moment.

More: [Failure modes](failure-modes.md) and
[Troubleshooting](troubleshooting.md).

## 5. Explain what you learned (~1–2 min)

- **Detection and tracking are separate problems.** 2123 of 11442 person
  detections were grey: detected, but not confirmed as tracks.
- **A confidence threshold is an application tradeoff.** 0.20 missed 19
  people and drew 92 wrong boxes; 0.40 missed 120 and drew 3.
- **Tracker IDs are not identities.** The clip produced 44 IDs, with at most
  12 confirmed tracks in any frame.
- **Media handling can look like a model bug.** Jumping to frame 545
  silently returned frame 531, so an early detection result described the
  wrong frame until PR 7 fixed frame reading.
- **Arithmetically valid evaluation can still be wrong.** The review passed
  both automatic checks while three frames disagreed about the same boxes.
- **Writing documentation exposed engineering problems.** Documenting the
  commands found that `evaluation generate` targets the committed review by
  default; checking numbers for the concept docs found the review
  inconsistency.

## Optional: Hosted Roboflow extension (~2–3 min)

Steps 1–5 are the local project: a pretrained model finds generic `person`s
and ByteTrack follows them. This optional part covers a separate experiment
on Roboflow's hosted platform that asked a different question: what changes
when the target is *rugby players* specifically? It changed no code in this
repository. Full write-up: [Hosted Roboflow experiment](hosted-roboflow.md).

| | Local demo | Hosted extension |
| --- | --- | --- |
| Question | Find and follow every person | Detect rugby players only |
| Model | Pretrained RF-DETR Nano, COCO `person` | RF-DETR Small fine-tuned on one class, `rugby player` |
| Runs | Locally, with ByteTrack tracking | On Roboflow, as a published Workflow (no tracking) |

Point out:

- **A product-specific class.** Referees, touch judges, spectators and
  sideline staff were deliberately not labelled, the opposite of the local
  review, where every person counted.
- **Auto Label plus review.** Auto Label sped up labelling 56 frames, but
  every image still needed checking: official and sideline boxes removed,
  missed players added, loose boxes fixed.
- **A clean baseline.** `v1-baseline`: 42/9/5 split, Fit (black edges) in
  512x512 to keep the wide aspect ratio, no augmentation.
- **Hosted metrics, qualified.** Validation mAP@50 86.7%, precision 93.2%,
  recall 77.9%, from 9 images of the same clip it trained on. A baseline,
  not proof it works on other games.
- **The unseen-match test.** One image from a different match: 24
  detections at 0.50 with an obvious player missed; at 0.30 that player came
  back along with roughly four more sideline/non-player boxes. The same
  tradeoff as step 3.
- **The Workflow and its first failure.** The Agent-built Workflow first
  failed on an invalid model ID. Fixing only that block, using the ID from
  the model picker, made it run and return 24 detections.

The lesson: a successful training job isn't the end of evaluation.

## 6. Questions this project can answer

**Why RF-DETR Nano?** It's the smallest pretrained RF-DETR size, and it
processed this clip faster than its 55 fps playback rate on the recorded GPU
run (72.7 frames/s in PR 5). Larger RF-DETR sizes weren't compared, so this
doesn't show Nano is the best choice.

**Why ByteTrack?** It's a general-purpose tracker in Roboflow's `trackers`
package that takes Supervision detections directly. It also uses
lower-confidence detections to keep existing tracks alive, a design aimed at
people who are partly hidden and score lower. No other tracker was compared.
[Tracking](tracking.md#how-bytetrack-uses-lower-confidence-detections)

**What happens when the confidence threshold changes?** Lowering it adds
boxes: more real people and more wrong boxes. See the table in step 3.
[Detection](detection.md#the-confidence-threshold)

**Why are there more tracker IDs than people?** Each new track gets a new
ID. Fragments after the pan, players re-entering view and ID switches all add
IDs. [Tracking](tracking.md#an-id-is-not-a-players-identity)

**What caused the fast-pan fragmentation?** The pan at frames 825–829 was
the largest sustained frame-to-frame change in the clip. ByteTrack predicts
where each box moves from its past motion, so when the camera swings,
everyone appears to jump and tracks are lost. Some new IDs are probably the
same players; that wasn't verified person by person.
[PR 005 note](learnings/PR-005-video-tracking.md)

**What's the difference between an unconfirmed and a missed detection?** A
missed person has no box: the detector didn't find them. An unconfirmed
person has a grey box: the detector found them, and the tracker returned no
confirmed ID. [Failure modes](failure-modes.md#6-a-person-has-a-box-but-it-says-unconfirmed)

**Why isn't this evaluation COCO mAP?** It's 20 correlated frames from one
clip, counted by one reviewer, with no drawn ground-truth boxes and no IoU
scoring. It shows the threshold tradeoff on this footage; it can't be
compared with published benchmarks.
[Evaluation](evaluation.md#why-this-is-not-formal-coco-map)

**What would you improve next?** *Future work, not implemented:* test
camera-motion compensation (for example BoT-SORT) against the pan
fragmentation; give ByteTrack lower-threshold detections and compare; make
`evaluation generate` default to a path under `outputs/`; use container
timestamps instead of the approximate `frame / fps` seconds.

**How would this change for a production or custom rugby model?** *Future
work, not implemented:* fine-tune on labelled rugby footage (for example to
separate players from officials); evaluate on many clips with drawn
ground-truth boxes, IoU matching and more than one reviewer; measure tracking
with labelled tracks; and handle non-gameplay content such as the screen
overlay at the end of the project's clip. A small hosted experiment has
since fine-tuned a one-class `rugby player` model with officials left
unlabelled; see [Optional: Hosted Roboflow extension](#optional-hosted-roboflow-extension-23-min).

## 7. Useful links

- [Getting started](getting-started.md)
- [Commands](commands.md)
- [How it works](how-it-works.md)
- [Detection](detection.md)
- [Tracking](tracking.md)
- [Evaluation](evaluation.md)
- [Failure modes](failure-modes.md)
- [Troubleshooting](troubleshooting.md)
- [Glossary](glossary.md)
- [Hosted Roboflow experiment](hosted-roboflow.md)
- [Learning notes](learnings/README.md)
