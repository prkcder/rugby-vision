# PR 011 - Failure Modes and Troubleshooting Guides

## What I Built

Two guides for a technical user who is looking at a bad result and needs to
find which part of the pipeline caused it, plus README navigation. No code
changed.

- **`docs/failure-modes.md`**: the pipeline layers (input, detection,
  filtering, tracking, annotation, evaluation), a summary table, and 15
  failure modes observed in this project. Each has the same block: symptom,
  likely layer, what was observed, what it doesn't necessarily mean, and a
  link to the concept guide or learning note with the details.
- **`docs/troubleshooting.md`**: a "which layer failed?" decision list, then
  ordered checks for each symptom (no box, too many boxes, grey box, new IDs,
  ID switch, threshold changes, wrong frame, inconsistent evaluation,
  warnings), and a checklist of what to collect when reporting a problem.
- **`README.md`**: the Documentation table now links the four concept guides
  from PR 010 and the two new guides. The "more guides are planned" line was
  removed.

## What I Learned

- **A bad final result doesn't automatically mean the model failed.** The
  same visible outcome can belong to different layers:
  - no box → detection;
  - grey `unconfirmed` box → detection succeeded, tracker confirmation
    didn't;
  - a person's ID changes → tracking continuity (fragmentation);
  - an ID moves to someone else → tracking association (ID switch);
  - wrong picture for a frame number → media/input;
  - counts that contradict each other → the evaluation process.
- **Failure mode and troubleshooting action are different questions.** The
  failure-modes page answers "what is this and who owns it?", with evidence.
  The troubleshooting page answers "what do I check, in what order?". Keeping
  them separate stopped the checks from turning into explanations, and the
  explanations from turning into instructions.
- **The frame check has to come first.** Every other diagnosis assumes the
  right frame. The tracked video has no frame numbers drawn on it, and on
  this variable-frame-rate clip a player's time doesn't equal
  `frame index / fps`, so the reliable way to inspect a frame is
  `detection --frame-index N`.
- **The reviewer's notes describe hard cases, not individual misses.**
  Checking each quoted note against `review.csv` showed that the notes about
  cropped people (frame 179), hidden people (frame 640) and a person visible
  mainly as legs (frame 435) are all on frames where every person was found at
  0.20. People went missing on those frames only at higher thresholds, and
  the review stores counts, not which person was missed. So the guide says
  these cases score lower, not that each note explains a specific miss.
- **Some symptoms look like model failures but aren't.** The end of the clip
  loses all detections because a phone/YouTube overlay covers the match; that
  is the input changing, not RF-DETR or ByteTrack failing.

## Important Terms

- **Failure mode**: a recurring way a system produces a wrong result, named
  by its symptom and the layer that owns it.
- **Pipeline layer**: one stage of the pipeline with its own responsibility,
  such as detection or tracking.
- **Triage**: deciding which layer a problem belongs to before trying to fix
  it.

## Problems I Hit

1. **Symptoms that point at the wrong layer.** "This player has no ID" can be
   a detection miss or a tracking confirmation issue, and the two need
   different fixes. A reader who only sees the output can't tell them apart
   without knowing the grey `unconfirmed` style.
2. **The first draft attributed misses to specific reviewer notes.** It
   listed "two cropped spectators" and "some players partially hidden" as
   examples of people with no box. Those rows have 0 false negatives at 0.20.
3. **Blur was a tempting cause to list.** Frame 844 is noted as a "blurry
   running scene", but all 8 people there were found at 0.20, and its later
   misses are noted as a box spanning two people.
4. **Overlap with the concept guides.** Most failure modes are already
   explained in `detection.md`, `tracking.md` or `evaluation.md`.
5. **Warnings vs failures.** A new user sees several warnings before any
   output, and can't tell them from a real error.
6. **Evaluation on another video.** Detection, tracking and
   `evaluation generate` all accept `--video`, but evaluation samples fixed
   frame positions designed around this clip. Another video must be long
   enough for them, and they may not land on useful gameplay moments, so
   "run it on your own video" means something different for evaluation.

## How I Solved Them

1. Put the layer decision first in the troubleshooting guide, and gave the
   no-box and grey-box cases separate sections.
2. Rewrote the passage to say those hard cases score lower and that the
   review doesn't record which person was missed.
3. Listed blur as noted in the review but not shown to cause misses in this
   sample.
4. Kept each failure mode to its evidence and what it doesn't mean, and
   linked to the concept guide for the explanation. The ByteTrack settings
   table, metric definitions and seeking investigation aren't repeated.
5. Re-ran single-frame detection to confirm the exact warning text, listed
   only the warnings observed, separated them from the real command errors
   seen in earlier PRs, and said that "didn't stop the run" isn't the same as
   "always harmless".
6. Stated the limitation in the evaluation section and linked to Getting
   started instead of repeating setup instructions.

### Verification

- Every quoted reviewer note was checked against `data/evaluation/review.csv`,
  and the per-threshold FP/FN totals were recomputed from it.
- Tracking and media figures (2123 of 11442 unconfirmed, 44 IDs, at most 12
  confirmed tracks per frame, the pan and `#22`/`#30` frames, 545→531,
  9.88s vs about 10.08s, the overlay frames) were checked against the
  PR 005, PR 006 and PR 007 notes and `tracking.md`.
- Single-frame detection on frame 545 was re-run: the same 11 confidences as
  PR 007, and the four warning messages listed in the guide.
- A script resolved every relative link and anchor in the README and docs.
- `markdownlint-cli2` (line-length rule off) reported 0 issues on the
  changed files.
- `pytest`, `ruff check src tests` and `ruff format --check src tests`
  passed.

## What I Would Explain to a Customer

When the output looks wrong, the first question isn't "is the model bad?"
but "which step went wrong?". The project runs in layers: reading the
video, finding people, linking them over time, drawing, and measuring. A
missing box, a grey box, a changed ID and a strange metric look like the
same problem from the outside, but each one belongs to a different layer and
has a different fix.

The new guides list the failures we actually saw on this footage, which
layer owns each one, and the checks to run in order. For example, a grey
box means the detector found the person and only the tracker hadn't
confirmed them yet, and the empty frames at the end of the clip come from a
phone overlay covering the match, not from the model.

## Remaining Questions

- Should the tracked video show the frame number, so a frame seen in the
  output can be looked up directly?
- The review can't say which specific person was missed. Would recording
  missed people per frame be worth the extra review effort?
- Should the source clip be trimmed before the overlay, rather than every
  guide explaining the end of the clip?
