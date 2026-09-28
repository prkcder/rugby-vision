# PR 009 - Evaluation Review Correction

## What I Built

A correction to the manual detection review from PR 006. Three rows of
`data/evaluation/review.csv` were re-reviewed and changed:

| Frame (0.20) | Before TP / FP / FN | After TP / FP / FN |
| --- | --- | --- |
| 384 | 11 / 15 / 7 | 17 / 9 / 1 |
| 742 | 9 / 13 / 6 | 15 / 7 / 0 |
| 793 | 9 / 11 / 5 | 14 / 6 / 0 |

The `detected_count`, `occlusion_level` and `notes` values in those rows
didn't change. The notes describe what is visible in the frame, and they're
still accurate. The fact that the rows were re-reviewed is recorded here
rather than in the CSV.

`summarize` on the corrected review:

```text
threshold frames   TP   FP   FN precision  recall     F1
     0.20     20  359   92   19     0.796   0.950  0.866
     0.40     20  258    3  120     0.989   0.683  0.808
     0.60     20  169    0  209     1.000   0.447  0.618
```

At 0.20 this was TP 342, FP 109, FN 36, precision 0.758, recall 0.905 and
F1 0.825. The 0.40 and 0.60 rows are unchanged, and ground truth is still
378 people.

The summary tables in `docs/commands.md` and `docs/getting-started.md`, and
the results and customer summary in the
[PR 006 learning note](PR-006-detection-evaluation.md), now show the
corrected numbers. PR 006 also has a follow-up section with the original
values. `evaluation.py` and the tests weren't changed.

## What I Learned

### How it was found

While writing concept documentation, every number quoted from the review
was checked against `review.csv`. Three dense maul frames had **fewer**
true positives at 0.20 than at 0.40:

- frame 384: 11 at 0.20 vs 12 at 0.40
- frame 742: 9 vs 11
- frame 793: 9 vs 13

That is only possible if the 0.20 image is missing some of the 0.40 boxes.
So the next step was to check whether it was.

### The prediction sets are nested

RF-DETR Nano was re-run on these frames at all three thresholds with a
throwaway script (not committed). On frames 384, 742 and 793:

- the person-box counts matched the CSV's `detected_count` exactly (for
  example 8, 13 and 20 on frame 793);
- every box at 0.60 was also present at 0.40, and every box at 0.40 was
  also present at 0.20, with matching coordinates.

An earlier check had found the same 0.40-to-0.20 nesting on frame 25.

So lowering the threshold only **adds** boxes. It never removes or moves
the ones already there.

### Arithmetic consistency is not semantic consistency

The PR 006 validator checks two rules:

- `TP + FP == detected_count`: every box drawn is judged exactly once in
  its own row.
- `TP + FN` is the same at every threshold: the frame's ground truth
  doesn't depend on the model.

Both passed on the original counts. They prove that each row adds up and
that the ground truth is stable. They don't prove that the rows for one
frame **agree with each other** about the same boxes.

Frame 793 shows the gap:

- At 0.40 there were 13 boxes, all 13 judged true positives.
- All 13 of those boxes are also drawn at 0.20, plus 7 more.
- Under the one-to-one matching rules, each of those 13 boxes still matches
  its own distinct person at 0.20. The extra 7 boxes can add true positives
  or false positives, but can't take any away.
- So a consistent review can't go from 13 TP at 0.40 to 9 TP at 0.20. The
  original row said 9 TP, 11 FP, 5 FN, and it still passed both checks,
  because 9 + 11 = 20 boxes and 9 + 5 = 14 people.

The likely cause is that each threshold's image was counted separately.
The 0.20 images of these mauls have many overlapping boxes, and the
original notes say so ("overlapping boxes difficult to inspect",
"difficult to separate"). Some boxes that were counted as correct at 0.40
were probably counted as duplicates at 0.20.

### How the box-by-box review fixed it

The re-review used material generated outside the repository, in the
gitignored `outputs/evaluation/rereview/`:

- images where each box keeps the **same number** at every threshold,
  coloured by the highest threshold it survives;
- views showing only the boxes each lower threshold adds;
- a crop of every box with surrounding context;
- a worksheet with **one row per box**, recording which person it matches
  or why it's a false positive.

Each prediction was judged **once**, and that judgment carried to every
threshold where the box appears. At 0.20, only the boxes first appearing at
0.20 needed new judgments. Each one was either:

- a true positive for a person still unmatched after 0.40; or
- a false positive: a duplicate of someone already matched, a box spanning
  people already matched, or a false detection.

The existing matching rules were unchanged. Every judgment was made by the
reviewer; the code only drew the boxes and checked the totals. Where a wide
0.40 box could have matched more than one person, the reviewer decided which
person it matched, and the new boxes were judged against that.

The re-review gave:

| Frame | Ground truth | New 0.20 boxes | New TPs | New FPs | 0.20 TP / FP / FN |
| --- | --- | --- | --- | --- | --- |
| 384 | 18 | 14 | 5 | 9 | 17 / 9 / 1 |
| 742 | 15 | 11 | 4 | 7 | 15 / 7 / 0 |
| 793 | 14 | 7 | 1 | 6 | 14 / 6 / 0 |

Ground truth for each frame was re-checked against the clean reference and
kept. The 0.60 and 0.40 judgments were kept as reviewed. After the
correction, TP never falls as the threshold is lowered, on any of the 20
frames.

### What changed in the conclusions

- The ordering is the same: 0.20 has the highest recall and the lowest
  precision.
- 0.20 now has the highest F1 of the three thresholds tested (0.866 vs
  0.808 at 0.40). PR 006 had described the two F1 scores as close.
- That doesn't make 0.20 a universally best setting. Across the whole
  sample it still draws 92 wrong boxes, against 3 at 0.40. The choice still
  depends on whether a missed person or a wrong box costs more.

## Important Terms

- **Nested prediction sets**: every box kept at a higher threshold is also
  kept, unchanged, at a lower one.
- **Arithmetic consistency**: each row's counts add up (`TP + FP` = boxes
  drawn, `TP + FN` = ground truth).
- **Semantic consistency**: the same box gets the same judgment wherever it
  appears, so rows for different thresholds agree.
- **Box-level review**: judging each predicted box once, by a stable ID,
  instead of re-counting each threshold's image from scratch.

## Problems I Hit

1. **The first numbered images were unreadable in the maul.** On frame 384,
   26 boxes overlap in a small area, and labels hid each other.
2. **One combined image of every new box was too small to judge.** When
   shown at a readable width, 14 tiles of the maul lost too much detail.
3. **Some 0.40 boxes cover more than one person.** A wide box (for example
   #10 on frame 742, #8 on frame 793) could be matched to several people,
   and which one it matches changes whether a new box is a true positive.

## How I Solved Them

1. Added a crop of every box with its number, confidence and first
   threshold, and views showing only the boxes each threshold adds.
2. Made one tile per new box, with the 0.40 boxes outlined in grey, and
   compared them at full resolution in pairs. The overlap (IoU) of each new
   box with the 0.40 boxes was listed alongside.
3. Asked the reviewer which person each wide box matched before judging the
   new boxes, and recorded the answer in the worksheet notes.

## What I Would Explain to a Customer

We found and fixed a counting inconsistency in our own manual evaluation.

At the lowest setting, three crowded frames had been scored as if the
detector found fewer people than at a stricter setting. That can't happen
here: we confirmed that lowering the setting only adds boxes on top of the
ones already there. We re-checked those frames one box at a time, keeping
each box's judgment the same across settings.

The corrected result is better for the lowest setting than first reported:
it finds about 19 in 20 people, with about 1 in 5 boxes wrong. The stricter
settings are unchanged. The lesson is that automatic checks that each row
adds up aren't enough; the rows also have to agree with each other.

## Remaining Questions

- **Should `summarize` check that TP never falls as the threshold is
  lowered?** That rule is only valid when the lower-threshold boxes contain
  the higher-threshold ones. The CSV stores counts, not box identities or
  coordinates, so `summarize` can't prove that from the CSV alone. The check
  would need either stored box data or a documented assumption that the
  model's outputs are nested.
- **Should nesting be confirmed on all 20 frames?** It was confirmed on
  frames 25, 384, 742 and 793. The other frames pass the "TP never falls"
  check, but that doesn't prove their boxes are nested.
- **Would a box-by-box review change the other 17 frames?** They were
  counted image by image, like the original three. Their counts are
  consistent across thresholds, but they weren't re-reviewed box by box.
- **Would a second reviewer agree?** The re-review was done by the same
  single reviewer as the original.
