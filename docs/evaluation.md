# Evaluation

This page explains how Rugby Vision measures how well the person detector
works: what was counted, how it was counted, what precision, recall and F1
mean, and what the numbers can and can't tell you.

It builds on [Detection](detection.md). For the commands, see
[Commands](commands.md#evaluation-generate). Short definitions are in the
[Glossary](glossary.md).

## Why evaluation is necessary

Looking at a few annotated frames gives an impression, not a measurement. A
frame where every player has a box looks convincing, but it says nothing
about the frame where half the maul was missed.

Evaluation replaces impressions with counts. It answers questions like:

- Of the boxes the model drew, how many were real people?
- Of the real people, how many got a box?
- How do those answers change when the confidence threshold changes?

Without that, there is no fair way to choose a threshold or to tell whether a
change made things better.

## Ground truth

To judge the model, you need to know the right answer. The right answer is
called **ground truth**.

In this project, ground truth comes from a person, not from code. A reviewer
looked at 20 frames of the clip and counted the real people in each. The
code saves the images and a CSV to fill in, then checks the filled-in
numbers. It never decides what counts as a person.

The 20 frames contain **378 people** in total, between 8 and 27 per frame.

## The review policy

A count is only meaningful if every frame is counted the same way. These are
the rules the review followed.

**Who counts as a person:**

- Any human the reviewer can confidently see as a separate person counts,
  even if partly cropped or hidden.
- Players, referees, touch judges and sideline spectators all count. The
  model predicts COCO's general `person` class, not a rugby "player" class,
  so a spectator it boxes is a correct detection of a person.
- An ambiguous, isolated arm, leg or body fragment doesn't count, unless a
  separate person can be confidently identified from it.

**How boxes are matched to people:**

- One box can match at most one person.
- One person can be matched by at most one box.
- **One box spanning two people** counts as 1 true positive and 1 false
  negative. The box can only match one of them, so the other is missed.
- **Two boxes on one person** count as 1 true positive and 1 false positive.
  The extra box is a duplicate.
- **A badly placed box** still counts as a true positive if it corresponds to
  one unique real person. Poor placement alone isn't a false positive. (See
  [Detection](detection.md#a-badly-placed-box-is-not-the-same-as-a-wrong-box).)

## True positives, false positives and false negatives

Every box and every real person ends up in exactly one of three buckets:

| Term | Plain meaning | Examples from the review |
| --- | --- | --- |
| **True positive (TP)** | A box on a real person, and that person's only matched box | Most boxes at 0.40 and 0.60 |
| **False positive (FP)** | A box with no real person of its own | "bag detected as person", "touch judge flag detected as person", duplicate boxes in a maul |
| **False negative (FN)** | A real person with no box of their own | A hidden player with no box; the second person under a box that spans two |

There is no fourth bucket for "a real person the model correctly ignored".
Detection has no fixed list of empty spots to check, so there are no true
negatives to count.

## Two rules the counts must obey

The CSV's counts have to satisfy two checks. `evaluation summarize` refuses
to print metrics if either fails.

### TP + FP = detected_count

Every box the model drew gets judged as either a true positive or a false
positive. Nothing is skipped or marked "unsure". So for every row:

```text
true positives + false positives = number of boxes drawn
```

If the reviewer's numbers don't add up to the box count, a box was missed or
double-counted during review.

### TP + FN stays the same across thresholds

`TP + FN` is every real person in the frame: the ones the model found plus
the ones it missed. That's the frame's ground truth.

The people in a frame don't change when the model's threshold changes. So for
one frame, `TP + FN` must be the same at 0.20, 0.40 and 0.60.

Frame 25 shows this. It has 26 people:

| Threshold | Boxes drawn | TP | FP | FN | TP + FN |
| --- | --- | --- | --- | --- | --- |
| 0.20 | 33 | 26 | 7 | 0 | 26 |
| 0.40 | 17 | 16 | 1 | 10 | 26 |
| 0.60 | 10 | 10 | 0 | 16 | 26 |

As the threshold rises, people move from TP to FN, but the total stays at
26.

## Precision, recall and F1

The three metrics each answer one question.

**Precision: when the model draws a person box, how often is it a real
person?**

```text
precision = TP / (TP + FP)
```

High precision means few wrong boxes.

**Recall: of all the real people, how many did the model find?**

```text
recall = TP / (TP + FN)
```

High recall means few missed people.

**F1: how good is the balance between the two?**

```text
F1 = 2 × precision × recall / (precision + recall)
```

F1 is only high when both precision and recall are high. A model that
draws one perfect box and misses everyone else has perfect precision but a
very low F1.

The project adds up TP, FP and FN across all 20 frames first, then calculates
each metric once per threshold. Crowded frames therefore count for more than
sparse ones.

## The results

The validated summary from the completed review, as recorded in
[PR 006](learnings/PR-006-detection-evaluation.md). These are the current
results, including a correction to three frames described
[below](#why-the-policy-must-be-consistent):

```text
threshold frames   TP   FP   FN precision  recall     F1
     0.20     20  359   92   19     0.796   0.950  0.866
     0.40     20  258    3  120     0.989   0.683  0.808
     0.60     20  169    0  209     1.000   0.447  0.618
```

`TP + FN` is 378 at every threshold, matching the ground truth.

## The confidence-threshold tradeoff

Reading the table from top to bottom:

- Raising the threshold from 0.20 to 0.60 cut false positives from 92 to
  0, so **precision rose**.
- Over the same range, true positives fell from 359 to 169, so **recall
  fell**.
- **F1** was highest at 0.20 (0.866), lower at 0.40 (0.808) and much lower
  at 0.60 (0.618).

The highest F1 doesn't make 0.20 the right choice for every application.
F1 shows how well precision and recall are balanced, but it doesn't know
whether a wrong box or a missed person costs more. 0.20 misses 19 people
but draws 92 wrong boxes; 0.40 draws only 3 wrong boxes but misses 120
people. Which one suits an application depends on which mistake costs
more. [Detection](detection.md#there-is-no-universally-best-threshold)
discusses that choice.

The 0 false positives at 0.60 were observed in this sample. They don't mean
the model can't make a mistake at 0.60.

## Why the policy must be consistent

Metrics from different thresholds can only be compared if every image was
judged by the same rules. If a duplicate box were an FP in one frame but
ignored in another, a change in precision might reflect the reviewer, not the
model.

The two checks above catch arithmetic mistakes. They can't catch every
judgment inconsistency, and one turned up while writing this page:

- On three dense maul frames (384, 742 and 793), the original review
  recorded **fewer** true positives at 0.20 than at 0.40.
- That can't be right. On those frames, every box drawn at 0.40 is also
  drawn at 0.20, so a box that was a true positive at 0.40 is still one at
  0.20.
- The three frames were re-reviewed box by box, with each box judged once
  and that judgment carried to every threshold where it appears.

The results on this page are the corrected ones. The
[PR 009 learning note](learnings/PR-009-evaluation-review-correction.md)
has the full story, including the original numbers.

## Why this is not formal COCO mAP

Published detection benchmarks, including RF-DETR's, usually report **mAP**
(mean average precision) on the COCO dataset. That method:

- uses thousands of images with ground-truth boxes drawn by annotators;
- matches each predicted box to a ground-truth box by **IoU** (how much the
  two boxes overlap), so badly placed boxes are penalised;
- averages precision over every confidence level and several IoU cutoffs.

This project's evaluation is much simpler:

- **20 frames**, from **one clip**.
- **One reviewer**, with no second reviewer to check agreement.
- **Temporally correlated frames.** They are about a second apart, from the
  same match and camera, so they aren't 20 independent samples.
- **Simplified count matching.** The reviewer counted matches by eye; no
  ground-truth boxes were drawn.
- **No IoU localization scoring.** A badly placed box can still be a TP.
- **Only three thresholds**, not a sweep over all of them.

So these numbers **can't be compared with published RF-DETR benchmark
results**. They describe how this model behaves on this footage under these
rules, which is what was needed to understand the threshold tradeoff.

## Next

- [Detection](detection.md): what the model does and why it makes mistakes
- [Tracking](tracking.md): what happens to the detections next
- [PR 006 learning note](learnings/PR-006-detection-evaluation.md): frame
  selection, reviewer notes and the full per-threshold discussion
- [Glossary](glossary.md): short definitions
