# PR 010 - Core Computer Vision Concept Documentation

## What I Built

Four concept guides for a reader who is comfortable with software but new to
computer vision, plus this note. No code changed.

- **`docs/detection.md`**: object detection, what RF-DETR does here, boxes,
  classes and confidence, the `person` filter, inference vs training, the
  confidence threshold and its tradeoff, why rugby footage is hard to
  detect on, and poor localization vs a false detection.
- **`docs/tracking.md`**: detection vs tracking, ByteTrack's role, tracks
  and `tracker_id`, association, the two-round use of low-confidence boxes,
  confirmed vs unconfirmed (`-1`), lost tracks, fragmentation, ID switches,
  occlusion, frame rate, and why the observed problems are a baseline rather
  than a verdict on ByteTrack.
- **`docs/evaluation.md`**: ground truth, the review policy, TP/FP/FN, the
  two consistency rules, precision/recall/F1, the current results table
  (including the PR 009 correction), the threshold tradeoff, and why this
  isn't COCO mAP.
- **`docs/glossary.md`**: 27 short, alphabetized definitions.

Each concept follows the same order: plain language, how it appears in the
project, the precise term, a real example, then a link to the learning note
with the full story.

The four guides link to each other and to the existing docs and learning
notes. Nothing links *to* them yet. README and navigation changes were
deliberately left for the next docs PR.

## What I Learned

- **Documenting ByteTrack's thresholds meant reading the installed source.**
  The values in `trackers` 2.6.0 are `high_conf_det_threshold=0.6`,
  `track_activation_threshold=0.7`, `minimum_consecutive_frames=2`,
  `minimum_iou_threshold=0.1` and `lost_track_buffer=30`. Constructing
  `ByteTrackTracker(frame_rate=55.17997)` gave `maximum_frames_without_update
  = 56`, matching PR 005. The docs label these as that version's defaults,
  not as ByteTrack behavior in general.
- **Reading the source also showed two details the earlier notes didn't
  mention:**
  - Association uses an optimal assignment (`linear_sum_assignment`) that
    maximizes total IoU, not a greedy "best overlap first" match.
  - An unconfirmed track is dropped as soon as it misses a frame. Only
    confirmed tracks get the lost-track grace period.
- **With RF-DETR at 0.5, ByteTrack's low-confidence round only sees boxes
  from 0.5 to just under 0.6.** This follows from the two thresholds and
  explains why the low-confidence round has little to work with in this
  project.
- **Checking the numbers exposed an inconsistency in the manual review.**
  - While checking numbers against `review.csv`, I found that frames 384,
    742 and 793 had fewer TPs at 0.20 than at 0.40 (11 vs 12, 9 vs 11, 9 vs
    13).
  - I re-ran RF-DETR Nano on frames 25, 384, 742 and 793 with a throwaway
    script (not committed). The person-box counts were 33/17, 26/12, 22/11
    and 20/13 at 0.20/0.40, matching the CSV's `detected_count`. On all four
    frames, every 0.40 box was also present at 0.20.
  - So each 0.20 image contains every box that was a TP at 0.40, and a
    consistent review would count at least as many TPs at 0.20. Both
    existing checks (`TP + FP = detected_count`, constant `TP + FN`) still
    passed on these frames, so `summarize` couldn't see the problem.
  - Because these docs quote the review's metrics, this PR was paused so
    the source data could be fixed first. PR 009 re-reviewed the three
    frames box by box and corrected their 0.20 rows (see the
    [PR 009 learning note](PR-009-evaluation-review-correction.md)).
  - The concept docs were then updated to the corrected numbers.
    `evaluation.md` mentions the correction in a few lines and links to
    PR 009 rather than repeating it.
- **Not every hard-footage example supports the obvious claim.** Frame 844
  is noted as a "blurry running scene", but all 8 people there were found at
  0.20. The docs mention blur without claiming this sample shows its cost.

## Important Terms

- **Localization**: how well a box fits the object it belongs to. A badly
  localized box can still be a true positive in this project's count-based
  review.
- **Optimal assignment**: pairing tracks with detections so the total
  overlap is as large as possible, instead of greedily taking the best pair
  first.
- **Baseline**: a first measurement under default settings, used as a
  reference to compare later changes against.

## Problems I Hit

1. **"Threshold" means four different things in this project:**
   - RF-DETR's `--threshold` (0.5 by default);
   - the evaluation's 0.20/0.40/0.60 comparison;
   - ByteTrack's 0.6 high-confidence split;
   - ByteTrack's 0.7 activation threshold.

   A sentence like "boxes below the threshold" is ambiguous without saying
   which one.
2. **`tracker_id == -1` doesn't always mean an unconfirmed *track*.** The
   requested glossary term was "unconfirmed track", but in `trackers` 2.6.0
   a `-1` box may be a new track awaiting confirmation, a 0.6–0.7 box too
   weak to start a track, or a low-confidence box that matched nothing. The
   last two have no track behind them at all.
3. **"Confirmed" and "confident" are easy to mix up.** A box can have high
   RF-DETR confidence and still be unconfirmed, and a confirmed track can
   continue on a low-confidence box.
4. **"Tracklet" isn't used consistently.** PR 005 defined it as a synonym
   for track. More commonly it means a short or broken piece of a track.
5. **Poor localization and false positives look alike in an image.** A box
   covering only a head looks like a mistake, but under the review policy it
   is a TP if it belongs to one unique person.
6. **F1 alone hides which kind of mistake is being made.** Before the
   PR 009 correction, 0.20 and 0.40 had nearly equal F1. In the corrected
   results 0.20 has the highest F1 (0.866 vs 0.808), yet it draws 92 wrong
   boxes against 3 at 0.40. Either way, one threshold mostly misses people
   and the other mostly draws wrong boxes.
7. **The first glossary draft used `term` / `: definition` lists.** GitHub
   doesn't render that syntax as a definition list.
8. **The first draft of detection.md quoted "bag detected as person" for
   frames 25, 128 and 179.** Checking the CSV showed only frames 25 and 179
   use that wording (frame 128 says "bags and extra/duplicate detections").
   It also attributed the frame 230 distance example to the evaluation
   images, when it came from the tracked video in PR 005.
9. **The first drafts quoted metrics that later changed.** Every 0.20 figure,
   and the plain-language summaries built on them, came from the review as
   it was before PR 009.

## How I Solved Them

1. Named the threshold each time. tracking.md has a table of the ByteTrack
   settings and a paragraph separating RF-DETR's threshold from
   ByteTrack's.
2. Kept the requested term, but defined it as "a person detection returned
   with `tracker_id == -1`" and listed all three causes in tracking.md.
3. Explained confirmation as a property of the track, and confidence as a
   property of one box, in separate sections.
4. Defined tracklet in the glossary by its common meaning and treated it as
   interchangeable with track in the guides.
5. Added a section to detection.md separating the two, and linked the
   evaluation policy to it.
6. Explained in both detection.md and evaluation.md that F1 summarizes the
   balance of precision and recall but doesn't know what each kind of
   mistake costs, so the threshold choice still depends on the application.
7. Rewrote the glossary as `**Term**: definition` paragraphs.
8. Rewrote both passages to match their sources.
9. After PR 009 merged, updated the 0.20 table rows and summaries ("about
   19 in 20 people", "about 1 in 5 boxes wrong"), and searched all five
   files for the old values.

### Avoiding duplication

| Topic | Where it's covered in full | What the new docs do |
| --- | --- | --- |
| Pipeline, tool responsibilities, BGR/RGB | `how-it-works.md` | Link |
| Command options and output | `commands.md`, `getting-started.md` | Link |
| Class ID 1 vs name filtering | PR 003 note | One paragraph plus link |
| `#22`/`#30` timeline, pan analysis | PR 005 note | Short summary plus link |
| Frame selection, reviewer notes, per-threshold discussion | PR 006 note | Link; only the policy, table and limitations are restated |
| Seeking and variable frame rate | PR 007 note | Not relevant; not repeated |

A paragraph-similarity check against the README, existing docs and learning
notes found one near match: the detection page's "one clip, one reviewer"
caveat restates PR 006's in different words.

### Verification

- **Numbers:** recomputed from the corrected `data/evaluation/review.csv`:
  - totals, precision, recall and F1 per threshold;
  - 378 people, 8–27 per frame;
  - frame 25 counts (33/17/10 boxes; TP 26/16/10);
  - every quoted reviewer note.

  Tracking figures (44 IDs, 2123 of 11442 unconfirmed, the `#22`/`#30`
  frames, the pan frames and the 0.51–0.65 scores) were checked against the
  PR 005 note.
- **ByteTrack defaults:** read from the installed `trackers` 2.6.0 source and
  confirmed by constructing the tracker.
- **Links:** a script resolved all 38 relative links and anchors in the
  five files, including the links to the PR 009 note.
- **Markdown:** `markdownlint-cli2` (run temporarily with `npx`, line length
  rule off) reported 0 errors on the five files.
- **Stale values:** after the PR 009 update, a search of the five files
  found none of the original 0.20 figures.
- **Repository checks:** `pytest` passed, `ruff check src tests` and
  `ruff format --check src tests` passed.

## What I Would Explain to a Customer

The project now has three short guides and a glossary covering the ideas
behind it:

- how the detector decides what is a person, and why its confidence setting
  is a tradeoff rather than a single right answer;
- how the tracker links people across frames, and why its numbers are not
  player identities;
- how the detector was measured, and why those measurements can't be
  compared with published benchmarks.

Every example comes from this project's own footage and review.

While writing them, we found that three of the densest frames had been
counted inconsistently at the lowest threshold. We fixed the source data
before publishing the guides, so they show the corrected results: at the
lowest setting the detector finds about 19 in 20 people, with about 1 in 5
boxes wrong. It showed that crowded, low-threshold images are the hardest to
judge by hand, and that automatic checks that each row adds up can't catch
every judgment slip.

## Remaining Questions

- Should `evaluation summarize` also check that TP never falls as the
  threshold is lowered? The rule only holds when lower-threshold boxes
  contain the higher-threshold ones, and the CSV stores counts rather than
  boxes, so it can't prove that on its own (see PR 009).
- Where should the README and `how-it-works.md` link to the new guides? This
  is planned for the next docs PR.
