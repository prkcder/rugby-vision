# Failure Modes

This page answers one question: **what kinds of failures did this project
actually observe, and which part of the pipeline owns each one?**

It doesn't re-explain detection, tracking or evaluation. For those, see
[Detection](detection.md), [Tracking](tracking.md) and
[Evaluation](evaluation.md). For step-by-step checks when you're looking at a
bad result, see [Troubleshooting](troubleshooting.md).

Every example below comes from the project's own clip, its manual review
(`data/evaluation/review.csv`) or its [learning notes](learnings/).

## The pipeline layers

```text
input / video        decode the right frames of the right content
  → detection        RF-DETR finds objects in one frame
  → filtering        keep only the person class
  → tracking         ByteTrack links boxes across frames and assigns IDs
  → annotation       Supervision draws boxes and labels; output is saved
  → evaluation       a reviewer's counts turn into precision and recall
```

Each layer can only work with what the layer before it gave it. A tracker
can't follow a person the detector missed, and an annotator can't draw a box
that doesn't exist.

That's why **similar-looking symptoms can come from different layers.**
"This player has no ID" can mean RF-DETR found no box (detection), or that it
found one and ByteTrack didn't confirm it (tracking). "The model missed people
on this frame" can mean the detector missed them, or that you're looking at a
different frame from the one you think (input). The fix depends on which
layer failed, so identify that first.

## Summary

| # | Symptom | Likely layer | What it means | Observed in this project |
| --- | --- | --- | --- | --- |
| 1 | Visible person has no box | Detection | RF-DETR scored them below the threshold, or not at all | 19 missed at 0.20, 209 at 0.60; cropped, hidden and distant people score lower |
| 2 | Box on something that isn't a person | Detection | A false positive that the person filter can't remove | Bags, a touch judge flag, empty space |
| 3 | Two boxes on one person | Detection | A duplicate: one TP plus one FP | Low-threshold maul frames |
| 4 | One box covers several people | Detection | A merged box: one TP plus an FN for each extra person | Frames 230, 384, 742, 844 |
| 5 | Box covers only part of a person | Detection | Poor localization, not a false positive | Head-only and poorly placed boxes |
| 6 | Grey box labelled `unconfirmed` | Tracking | Detected, but ByteTrack returned no confirmed ID | 2123 of 11442 person detections |
| 7 | Same person gets a new ID | Tracking | Fragmentation: the track was lost and restarted | Nine new IDs after a fast camera pan |
| 8 | An ID moves to another person | Tracking | ID switch during association | `#22` moved from the referee to a player |
| 9 | Far more IDs than people | Tracking | IDs count tracks, not people | 44 IDs; at most 12 confirmed tracks in any frame |
| 10 | Tracking is unstable in a crowd | Detection and tracking | Overlapping boxes make matching ambiguous | Ruck at frame 545, tackle at frame 230 |
| 11 | Wrong frame returned | Input / media | Seeking landed on a nearby frame | Historical: asked for 545, got 531 (fixed) |
| 12 | Source isn't gameplay | Input / media | The video content itself changed | Phone and YouTube UI over the last frames |
| 13 | Time in seconds doesn't match a player | Input / media | `index / fps` is approximate for this clip | 9.88s shown vs about 10.08s in the container |
| 14 | Review passes checks but is inconsistent | Evaluation | Rows add up but disagree about the same boxes | Historical: three maul frames (fixed) |
| 15 | Crowded frames are hard to review | Evaluation | Counts depend on consistent matching rules | Reviewer notes on dense mauls |

## Detection

### 1. A visible person has no box

- **Symptom:** you can see a person in the frame, but no box is drawn on them,
  not even a grey one.
- **Likely layer:** detection. RF-DETR returned no box for them above the
  confidence threshold.
- **What was observed:**
  - **Higher thresholds.** Across the 20 reviewed frames, 19 people were
    missed at 0.20, 120 at 0.40 and 209 at 0.60. On frame 25 alone, missed
    people went from 0 to 10 to 16.
  - **Hard cases score lower.** The review notes cropped people ("two
    cropped spectators", frame 179), hidden people ("some players partially
    hidden", frame 640) and people "visible mainly as legs" (frame 435). On
    those frames everyone was found at 0.20, and people went missing as the
    threshold rose. Lowering the threshold exposed more cropped, distant and
    partly hidden people. The review records counts, not which person was
    missed, so it doesn't say which of these caused each miss.
  - **Distant people** tend to score low. On a wide shot around frame 230,
    several distant people scored 0.51–0.65, just above the 0.5 default.
  - **Merged boxes** also leave people without a box of their own (see
    [4](#4-one-box-covers-several-people)).
  - **Blur** was noted in the review ("blurry running scene", frame 844), but
    this sample doesn't show that blur caused a miss: all 8 people on that
    frame were found at 0.20.
- **What it doesn't necessarily mean:** that the model can't see that person.
  Often RF-DETR did score them, just below the threshold you chose. It also
  doesn't mean the tracker failed; the tracker never received a box.
- **Read more:** [Why detection is hard on rugby footage](detection.md#why-detection-is-hard-on-rugby-footage),
  [Why a higher threshold can miss real people](detection.md#why-a-higher-threshold-can-miss-real-people)

### 2. A box appears on something that isn't a person

- **Symptom:** a `person` box on an object or on empty field.
- **Likely layer:** detection. The person filter only removes other classes;
  it can't remove a wrong `person` detection.
- **What was observed:** at 0.20, bags on frames 25, 128 and 179, a "touch
  judge flag detected as person" on frame 281, and empty-space detections on
  frame 25. At 0.40 one bag still got through on frame 25. At 0.60 no false
  positives were recorded in this sample.
- **What it doesn't necessarily mean:** a broken class filter. Also note that
  a box on a spectator, referee or touch judge is **correct**: they are all
  people, and the model has no rugby-specific classes.
- **Read more:** [Keeping only people](detection.md#keeping-only-people)

### 3. Duplicate boxes around one person

- **Symptom:** two or more overlapping boxes on the same person.
- **Likely layer:** detection, mostly at low thresholds.
- **What was observed:** reviewer notes at 0.20 record "extra/duplicate
  detections" (frames 25 and 128) and "many overlapping or duplicate
  detections" in a maul (frame 742). Under the review rules a duplicate is
  1 TP + 1 FP.
- **What it doesn't necessarily mean:** two people. In a dense maul, two
  close boxes may be two players or one duplicated player; that's exactly why
  these frames were hard to review (see [15](#15-manual-review-is-hard-in-crowded-scenes)).
- **Read more:** [The review policy](evaluation.md#the-review-policy)

### 4. One box covers several people

- **Symptom:** a single box wraps two players, typically in a tackle or maul.
- **Likely layer:** detection.
- **What was observed:** the review recorded "one box spans two people" at
  0.60 on frames 230, 384 and 742, and at 0.40 and 0.60 on frame 844. It
  happens at high thresholds too, so the box itself can be confident.
- **How it's scored:** the review's matching rules let one box match at most
  one person. So a box around two people counts as **1 TP + 1 FN**: one
  person is matched, the other is counted as missed. It isn't a false
  positive, because the box does belong to a real person.
- **What it doesn't necessarily mean:** that the missing person was invisible
  to the model; they are hidden inside someone else's box. A merged box also
  feeds tracking a single box for two people (see [10](#10-dense-overlap-makes-tracking-unstable)).
- **Read more:** [True positives, false positives and false negatives](evaluation.md#true-positives-false-positives-and-false-negatives)

### 5. Poor localization

- **Symptom:** the box fits badly, for example covering only a head or
  cutting off the legs, but it is clearly on the right person.
- **Likely layer:** detection.
- **What was observed:** "some boxes only cover heads but still correspond to
  people" (frame 640), "some boxes poorly localized" (frame 230) and "one
  poorly localized box" (frames 486 and 742), all at 0.40.
- **What it doesn't necessarily mean:** a false positive. A badly placed box
  that belongs to one unique real person counted as a TP. This project's
  evaluation counts people; it doesn't score box placement.
- **Read more:** [A badly placed box is not the same as a wrong box](detection.md#a-badly-placed-box-is-not-the-same-as-a-wrong-box)

## Tracking

### 6. A person has a box, but it says "unconfirmed"

- **Symptom:** a grey box labelled `unconfirmed 0.66` in the tracked video.
- **Likely layer:** tracking. RF-DETR detected the person; ByteTrack returned
  the box with `tracker_id == -1` instead of a confirmed ID.
- **What was observed:** 2123 of 11442 person detections (about 19%) were
  unconfirmed when drawn. On the wide shot around frame 230, distant people
  scoring 0.51–0.65 passed RF-DETR's 0.5 threshold but were below the 0.7
  ByteTrack needs to start a track, so they stayed grey.
- **What it doesn't necessarily mean:** a detection failure. The detector did
  its job. It also doesn't mean a low-confidence box: a new track scoring
  above 0.7 is grey until it has been matched on consecutive frames.
- **Read more:** [Confirmed and unconfirmed detections](tracking.md#confirmed-and-unconfirmed-detections)
  (including the settings table)

### 7. The same real person gets a new tracker ID

- **Symptom:** a player has one ID, then a moment later the same player has a
  new, higher ID.
- **Likely layer:** tracking. This is **fragmentation**: the track was lost,
  and when the person was detected again ByteTrack started a new track.
- **What was observed:** a fast camera pan at frames 825–829. Between frames
  824 and 860, nine confirmed IDs ended; between 865 and 900, nine new IDs
  (28–36) started as players came back into view. Some are probably the same
  players under new numbers; that wasn't verified person by person.
- **What it doesn't necessarily mean:** a different person. It also doesn't
  mean every track breaks on camera motion: `#22` stayed on the referee
  through the same pan, because detections kept arriving.
- **Read more:** [Fragmentation](tracking.md#fragmentation)

### 8. The same tracker ID moves to another person

- **Symptom:** an ID that was on one person ends up on someone else.
- **Likely layer:** tracking association. This is an **ID switch**.
- **What was observed:** around frames 850–874, `#22` was on the referee and
  `#23` on a navy-shirted player running in front of him. As they overlapped,
  `#23` stopped being matched and `#22`'s box stretched to cover both. By
  frames 870–874, `#22` was on the navy player, and the referee reappeared as
  `#30`. That single event was both an ID switch and a fragmentation.
- **What it doesn't necessarily mean:** a detector mistake. Both people were
  being detected; ByteTrack matches boxes by position and motion, not by
  appearance, so it couldn't tell them apart when they overlapped.
- **Read more:** [ID switches](tracking.md#id-switches),
  [PR 005 learning note](learnings/PR-005-video-tracking.md)

### 9. Many IDs over a short clip

- **Symptom:** the tracking summary reports far more IDs than there are
  people on the field.
- **Likely layer:** tracking, and not necessarily a failure.
- **What was observed:** 44 confirmed IDs over the 1091-frame clip. In any
  single frame there were at most 17 person detections and at most 12
  confirmed tracks.
- **What it doesn't necessarily mean:** 44 people. The count includes every
  time a track started: fragments after the pan, the referee's new `#30`,
  players leaving and re-entering view, and short-lived tracks.
- **Read more:** [An ID is not a player's identity](tracking.md#an-id-is-not-a-players-identity)

### 10. Dense overlap makes tracking unstable

- **Symptom:** in rucks, mauls and tackles, boxes pile up, IDs flicker, or one
  tracked box covers two players.
- **Likely layer:** detection and tracking together. Detection ambiguity
  (merged, duplicate or missing boxes) becomes association ambiguity: when
  boxes overlap heavily, two tracks' predicted positions can both overlap the
  same detection.
- **What was observed:** at frame 545 the ruck produced several heavily
  overlapping tracked boxes (`#9`, `#10`, `#15`, `#16`, `#17`). On the wide
  shot at frame 230, one tracked box (`#5`) covered two players in a tackle.
  The `#22` switch above started with one box stretching over two people.
- **What it doesn't necessarily mean:** that changing only the tracker would
  fix it. If the detector gives one box for two people, no tracker can give
  them separate IDs.
- **Read more:** [Occlusion and dense groups](tracking.md#occlusion-and-dense-groups),
  [Why detection quality limits tracking quality](tracking.md#why-detection-quality-limits-tracking-quality)

## Input / media

### 11. The requested frame isn't the frame returned

- **Symptom:** you ask for frame N and analyse a picture that is actually a
  different frame, with no error.
- **Likely layer:** input / media handling.
- **What was observed (historical):** before PR 007, `read_frame()` jumped to
  a frame with OpenCV's `CAP_PROP_POS_FRAMES` seek. On this H.264 clip with a
  variable frame rate, seeking to 545 returned frame 531, 80 returned 55 and
  831 returned 839; seeking to 1075 or later failed. PR 003's "frame 545"
  result really came from about frame 531.
- **Current behavior:** the project decodes frames in order up to the
  requested one, and returns exactly frame N. This was checked against an
  independent sequential decode of the real clip.
- **What it doesn't necessarily mean:** a model problem. The model was
  analysing a real frame, just not the one named.
- **Read more:** [PR 007 learning note](learnings/PR-007-exact-frame-reading.md)

### 12. The source stops being rugby gameplay

- **Symptom:** near the end of the clip, detections disappear and a few
  short-lived IDs appear.
- **Likely layer:** input / content. The video itself changes.
- **What was observed:** the clip is a phone screen recording of a YouTube
  player. The player's title bar and controls fade in from about frame 1025,
  and the phone's control centre covers the picture from frame 1073.
  Frames 1073–1090 have zero detections, and IDs 42 (13 frames) and 43
  (9 frames) appear just before. The evaluation excludes frames from 1024 on
  for this reason.
- **What it doesn't necessarily mean:** that RF-DETR or ByteTrack failed.
  There are no players to find once the overlay covers the match.
- **Read more:** [PR 005 learning note](learnings/PR-005-video-tracking.md),
  [PR 006 learning note](learnings/PR-006-detection-evaluation.md)

### 13. The time in seconds doesn't match the video player

- **Symptom:** a frame reported at 9.88s shows up at a slightly different
  time in a video player.
- **Likely layer:** input / media metadata.
- **What was observed:** the time shown in the detection summary and the
  evaluation captions is `frame_index / average fps`. This clip has a
  variable frame rate, so that's approximate: frame 545 is reported as 9.88s,
  while its container timestamp is about 10.08s.
- **What it doesn't necessarily mean:** the wrong frame. The frame number is
  exact; only the seconds value is approximate.
- **Read more:** [PR 007 learning note](learnings/PR-007-exact-frame-reading.md)

## Evaluation

### 14. Metrics pass validation but the review is still inconsistent

- **Symptom:** `evaluation summarize` accepts the review, but some numbers
  don't make sense side by side.
- **Likely layer:** evaluation / manual review.
- **What was observed (historical):** frames 384, 742 and 793 had **fewer**
  true positives at 0.20 than at 0.40. Every box drawn at 0.40 is also drawn
  at 0.20, so that can't be right. The rows still passed both validation
  checks. PR 009 re-reviewed the frames box by box and corrected them.
- **Arithmetic vs semantic consistency:** the checks prove each row adds up
  (`TP + FP` equals the boxes drawn) and that each frame's ground truth is
  stable (`TP + FN` is the same at every threshold). They can't prove that
  the rows agree about the **same boxes**. That second kind of consistency
  needs the reviewer.
- **What it doesn't necessarily mean:** that the model changed or that the
  validator is broken. The validator did what it was designed to do.
- **Read more:** [Why the policy must be consistent](evaluation.md#why-the-policy-must-be-consistent),
  [PR 009 learning note](learnings/PR-009-evaluation-review-correction.md)

### 15. Manual review is hard in crowded scenes

- **Symptom:** in dense frames it's hard to say which boxes are duplicates,
  which cover two people and who was missed.
- **Likely layer:** evaluation / manual review.
- **What was observed:** reviewer notes include "dense maul; overlapping
  boxes difficult to inspect" (frame 384), "maul; low-threshold boxes
  difficult to inspect" (frame 691) and "overlapping boxes make
  low-threshold review difficult" (frames 947 and 998). The inconsistency in
  [14](#14-metrics-pass-validation-but-the-review-is-still-inconsistent) came
  from frames like these.
- **Why explicit rules matter:** without the rule that one box matches at most
  one person and one person is matched by at most one box, the same duplicate
  or merged box
  could be counted differently from frame to frame, and a change in precision
  would reflect the reviewer rather than the model.
- **What it doesn't necessarily mean:** that the whole review is unreliable.
  It means the crowded, low-threshold rows carry the most judgment, and the
  review is one reviewer's counts on 20 frames.
- **Read more:** [The review policy](evaluation.md#the-review-policy),
  [PR 006 learning note](learnings/PR-006-detection-evaluation.md)

## Next

- [Troubleshooting](troubleshooting.md): what to check, in order, for each
  symptom
- [Glossary](glossary.md): short definitions
