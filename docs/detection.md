# Detection

This page explains object detection: what it is, what RF-DETR does in Rugby
Vision, and why the model sometimes misses people or finds people who aren't
there. It assumes no computer vision background.

For where detection sits in the pipeline, see
[How it works](how-it-works.md). For following people across frames, see
[Tracking](tracking.md). Short definitions of every term are in the
[Glossary](glossary.md).

## What is object detection?

Object detection answers two questions about a single picture: **what** is in
it, and **where** is it?

A detector doesn't describe the picture as a whole ("a rugby match"). It
lists individual objects: "a person here, another person there, a ball over
there." Each item in that list is one **detection**.

## What RF-DETR does in this project

RF-DETR is the detector. Rugby Vision uses **RF-DETR Nano**, the smallest
version, with weights that were already trained on **COCO**, a large public
dataset of everyday photos labelled with 80 kinds of object.

For each video frame, RF-DETR returns a list of detections. It looks at each
frame on its own and remembers nothing from earlier frames. Connecting
detections over time is the tracker's job (see [Tracking](tracking.md)).

## What a detection contains

Every detection has three parts. In the project's output, they appear as a
box plus a label such as `person 0.87`.

### Bounding box

A **bounding box** is a rectangle around the object. It's stored as four
pixel coordinates: the top-left corner and the bottom-right corner. Supervision
calls this format `xyxy`.

A box says roughly where the object is. It doesn't outline the object's exact
shape, so a box around a running player also contains some grass.

### Class

The **class** is the kind of object, such as `person`, `sports ball` or
`chair`. It is the `person` part of `person 0.87`.

The model can only choose from the classes it was trained on. COCO has
`person` but nothing rugby-specific, so RF-DETR can't tell a player from a
referee, a touch judge or a spectator. They are all `person`.

### Confidence

The **confidence** is a score from 0 to 1 showing how sure the model is about
the detection. It is the `0.87` in `person 0.87`.

Confidence isn't a probability of being correct that you can take at face
value. It's the model's own score, useful for ranking detections and for
deciding which ones to keep.

## Keeping only people

RF-DETR can report any COCO class. The project keeps only detections whose
class name is `person` and drops everything else. In code, this is the
`class_name == "person"` filter in `filter_people()` in
`src/rugby_vision/detection.py`.

Two things to know about this filter:

- **It filters by name, not number.** In this model's numbering, `person` is
  class `1`, not `0`, so matching on the readable name avoids picking the
  wrong class. The
  [PR 003 learning note](learnings/PR-003-rfdetr-detection.md) records how
  that was found.
- **It keeps every kind of person.** Players, referees, touch judges and
  spectators all pass, because the model has no way to separate them.

The filter only removes other classes. It doesn't remove wrong `person`
detections. If the model calls a bag a `person`, the bag stays.

## Inference, and what is not happening

Running an already-trained model on new pictures is called **inference**.
Everything RF-DETR does in this project is inference.

What the project doesn't do:

- **No training or fine-tuning.** The model has never seen rugby footage
  labelled for it. It works on this clip because people in rugby kit still
  look like the people in COCO's photos.
- **No rugby-specific classes.** There is no "player", "referee" or "ball
  carrier" class, only `person`.
- **No identity.** A detection says "a person is here", never *which* person.

## The confidence threshold

The **confidence threshold** is the minimum confidence a detection needs to
be kept. Anything scoring below it is thrown away before the project sees it.
The commands default to 0.5, set with `--threshold` (see
[Commands](commands.md)).

### Why a lower threshold shows more detections

The model scores many possible boxes. Most score low. Lowering the threshold
lets more of those low-scoring boxes through.

Some of those extra boxes are real people the model was unsure about: someone
far away, half hidden or cut off by the edge of the frame. Others are
mistakes: a duplicate box on someone already detected, a bag, a flag, or
empty space.

On frame 25 of the project's clip, the same model returned 33 person boxes at
0.20, 17 at 0.40 and 10 at 0.60. Every box kept at 0.40 was also among the
boxes at 0.20: lowering the threshold added boxes without replacing any.

### Why a higher threshold can miss real people

A high threshold keeps only the detections the model is most sure about.
That removes most mistakes, but it also removes real people who scored
lower. The model doesn't know they are real; it only knows it is less
confident about them.

### What this looked like in the project

The project's manual evaluation counted correct boxes, wrong boxes and
missed people on 20 frames at three thresholds:

| Threshold | Precision | Recall | F1 |
| --- | --- | --- | --- |
| 0.20 | 0.796 | 0.950 | 0.866 |
| 0.40 | 0.989 | 0.683 | 0.808 |
| 0.60 | 1.000 | 0.447 | 0.618 |

In plain terms:

- **Precision** is how many of the boxes were real people.
- **Recall** is how many of the real people got a box.
- **F1** combines precision and recall into one score. It's useful for
  comparing how well the two are balanced, but it doesn't know whether a
  wrong box or a missed person is more costly for your application.

[Evaluation](evaluation.md) explains how these were measured and exactly
what they mean.

What the table shows:

- **At 0.20,** the model found about 19 in 20 people, but about 1 in 5
  boxes was wrong. It had the highest recall and F1 of the three, and the
  lowest precision.
- **At 0.40,** almost every box was a real person, but about 1 in 3 people
  was missed.
- **At 0.60,** no wrong boxes were recorded, but more than half of the people
  were missed. The zero false positives happened **in this 20-frame sample
  only**. It doesn't mean the model never makes mistakes at 0.60.

### There is no universally best threshold

The threshold chooses which kind of mistake you would rather make:

- If **missing a person** is costly, for example when counting everyone on
  the field or when feeding a tracker, a lower threshold fits better, and the
  extra wrong boxes need to be tolerated or filtered.
- If **a wrong box** is costly, for example an alert that must never fire on
  a bag, a higher threshold fits better, accepting that more people will be
  missed.

In this sample, 0.20 had the highest F1. That's a useful summary, not a
decision: F1 doesn't know what each mistake costs you, and if a wrong box
costs more than a missed person, a higher threshold can still be the better
choice.

These numbers describe one clip and one reviewer. They show the shape of the
tradeoff on this footage, not a setting to copy to other footage.

## Why detection is hard on rugby footage

Rugby is difficult for a general-purpose detector. These are the causes the
project ran into, with examples from the clip. Quoted notes come from the
manual review described in [Evaluation](evaluation.md).

- **Distance.** Far-away people are small, with few pixels to go on, so they
  tend to get lower scores. In the tracked video, on a wide shot around
  frame 230, several distant people scored between 0.51 and 0.65, just
  above the 0.5 default. In the evaluation, lowering the threshold exposed
  more of these hard cases.
- **Cropping.** People cut off by the frame edge show only part of a body.
  The reviewer's notes mention "two cropped spectators" (frame 179) and
  "cropped legs still clearly belong to a person" (frame 793).
- **Occlusion.** When one person blocks another, the hidden person may be
  missed or only partly boxed. Notes include "some players partially hidden"
  (frame 640) and "one person visible mainly as legs" (frame 435).
- **Dense mauls and rucks.** Tightly packed players are the hardest case.
  Low thresholds produced "many overlapping or duplicate detections"
  (frame 742). Even at 0.60, one box sometimes spanned two people
  (frames 230, 384, 742 and 844), so one of the two people had no box of
  their own.
- **Low-quality footage.** The clip is an 832x384 phone screen recording of
  a match video, so there is less detail than in the original broadcast. The
  reviewer noted a "blurry running scene" at frame 844. In that frame all 8
  people were still found at 0.20, so this sample doesn't show how much blur
  alone costs.
- **Lookalike objects.** At low thresholds the model labelled some objects
  as people. At 0.20, the reviewer's notes record bags on frames 25, 128
  and 179, and a "touch judge flag detected as person" on frame 281. At
  0.40, a "bag detected as person" on frame 25 still got through.

## A badly placed box is not the same as a wrong box

Two different kinds of error are easy to mix up:

- **A false detection** is a box that doesn't belong to any real person of
  its own: a bag, a flag, empty space, or a second box on someone already
  boxed.
- **Poor localization** is a box that does belong to one real person but
  doesn't fit them well. It might cover only the head, or cut off the legs.

The project's evaluation noted boxes like this: "some boxes only cover heads
but still correspond to people" (frame 640) and "one poorly localized box"
(frames 486 and 742).

The evaluation counts people, not box accuracy. A poorly placed box still
counted as a correct detection if it matched one unique real person. It was
not counted as a false positive just for being badly placed. Scoring box
placement needs a different method, explained in
[Evaluation](evaluation.md#why-this-is-not-formal-coco-map).

## Next

- [Tracking](tracking.md): how detections are linked from frame to frame
- [Evaluation](evaluation.md): how the numbers above were measured
- [Glossary](glossary.md): short definitions
