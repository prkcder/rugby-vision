# PR 013 - Hosted Roboflow Experiment

## What I Built

Documentation of a Day 4 experiment on Roboflow's hosted platform. No code
in this repository changed.

- **`docs/hosted-roboflow.md`**: the full write-up. It covers a one-class
  `rugby player` dataset built from the project's clip with Auto Label and
  manual review, a `v1-baseline` version, a hosted RF-DETR Small training
  run and its metrics, a threshold test on an image from an unseen match,
  and a published Workflow.
- **`docs/demo.md`**: an optional 2–3 minute hosted section, plus two small
  updates so the local scope lines don't contradict it.
- **`README.md`**: a Documentation row for the new guide, and a scope line
  that now says the *local* pipeline uses pretrained models only.
- **`docs/learnings/README.md`**: this note in the index, and a hosted
  reading path.

What happened on the platform, in short:

```text
~20 s clip → ~3 fps sampling → 56 reviewed images, 1 class
  → Auto Label (GPT-6 Astra, Boxes) → manual review of every image
  → split 42 / 9 / 5 → v1-baseline (Auto-Orient, Fit 512x512, no augmentation)
  → RF-DETR Small, defaults, 0.44 credits, ended around epoch 46 of up to 100
  → validation mAP@50 86.7%, precision 93.2%, recall 77.9%, F1 84.9%
  → test AP@50 92.0% (5 images)
  → unseen-match image at 0.50 / 0.40 / 0.30: 24 / 25 / 29 detections
  → Workflow built by the Roboflow Agent, fixed, rerun, published
```

## What I Learned

### Generic `person` vs a class of your own

The local model's class is COCO's `person`, so its local review had to count
referees and spectators as correct. Defining `rugby player` flipped that: the
same box on a referee became a mistake. The model doesn't decide what is
correct; the class definition does. That definition had to be written down as
a label / don't-label policy before labelling started, including edge cases
like cropped, distant and partly hidden players and ambiguous body fragments.

### Auto Label still needed review

Auto Label's preview mostly worked, but it put `rugby player` boxes on some
officials and non-players, which is exactly the distinction the class exists
to make. Every image was reviewed after the full batch was auto-labelled:
official and sideline boxes removed, missed players added, loose and duplicate
boxes fixed. Auto Label made the first pass fast. The policy and the review
made the labels right.

### Correlated frames and leakage risk

All 56 images came from one ~20 second clip, sampled about a third of a
second apart. A random split puts near-identical neighbours into train,
validation and test. So the validation and test images aren't really new to
the model, and their scores say more about fitting this clip than about
rugby in general. This is the same limitation the local evaluation had with
its 20 correlated frames, now affecting a trained model.

### Why a baseline version

`v1-baseline` deliberately has no augmentation and default training
settings. With one variable changed at a time from here, any later
improvement or regression can be attributed to something. Changing data,
augmentation and hyperparameters together would leave a better or worse
number with no explanation.

### Aspect ratio

The source footage is wide. Stretch to 512x512 visibly distorted it. Fit
(black edges) in 512x512 kept the aspect ratio by padding. Preprocessing is
part of what the model learns from, so it's worth looking at the
preprocessed images, not just choosing a setting.

### Precision vs recall on validation

Validation precision was 93.2% and recall 77.9%. The model was relatively
conservative: most boxes it predicted were correct, while some players were
missed. It's the
same shape as the local 0.40 result (high precision, lower recall), from a
very different evaluation.

### Same-clip metrics vs generalization

The test-set AP@50 of 92.0% came from 5 images of the same clip. That's a
fine baseline and a weak claim. **A successful model-training job is not the
end of evaluation.** The unseen-match image showed things the same-clip
metrics couldn't: an obvious player missed at 0.50, and officials and
sideline people still getting boxes on unfamiliar footage.

### The threshold tradeoff, again

On the unseen image:

- 0.50: 24 detections, at least one obvious player missed;
- 0.40: 25 detections, the player still missed, one more sideline box;
- 0.30: 29 detections, the player recovered, with roughly four more
  sideline/non-player boxes.

The missed player and the extra sideline people scored in the same
confidence range, so none of the three thresholds kept one and dropped the
others. A threshold can't separate correct and incorrect detections whose
confidences overlap. It only chooses which mistake to make, which is the
lesson of the local review, reproduced on a different match with a different
model. No precision or recall was calculated for this image, because it has
no full ground-truth annotation.

### An Agent-built Workflow still needed debugging

The Roboflow Agent generated the Workflow structure successfully. The first
run still failed, in `detect_players`, with an invalid model ID / model
identifier format error. The Agent had used a short display identifier for
the model.

Asking it to investigate only the failing block, rather than rebuild the
Workflow, kept the fix small and checkable. It looked in the workspace model
picker, found the fully qualified deployable model ID, and changed only
`detect_players.model_id`. The input, the 0.50 threshold, both visualization
blocks and both outputs stayed the same. The rerun on the unseen image
returned the annotated image and predictions, with 24 detections, matching
the manual test at 0.50.

### Picking IDs instead of guessing them

The display name and the deployable model ID look similar but aren't
interchangeable. The model picker knows the real identifier; a person or an
agent typing one from memory can get it subtly wrong. Taking identifiers from
the workspace or the picker avoids that whole class of error.

### Documentation and customer-support lessons

- The same numbers can be honest or misleading depending on the sentence
  next to them. The metrics are documented together with image counts and
  the same-clip caveat, not on their own.
- The Workflow failure is documented, not hidden. "Invalid model ID" is
  exactly the kind of error a customer would hit, and the fix (use the model
  picker's ID, change only that field) is the useful part.
- A UI status can be wrong. The version builder showed `Unannotated: 56`
  while the images had their boxes attached. Checking the actual image views
  answered the question; the counter alone didn't.
- Account details don't belong in public docs. The model ID is written with
  a `<workspace>` placeholder.

## Important Terms

- **Custom class**: a class defined for one product, here `rugby player`,
  with its own labelling rules.
- **Annotation policy**: the written rules for what gets a box and what
  doesn't.
- **Auto Label**: labelling images with a model prompted by class name, to be
  reviewed by a person.
- **Dataset version**: a frozen snapshot of the dataset plus its
  preprocessing and augmentation settings.
- **Augmentation**: randomly altered copies of training images (flips,
  brightness and so on). None was used here.
- **Fit (black edges) vs Stretch**: resizing that keeps the aspect ratio by
  padding, vs resizing that distorts it to fill the square.
- **Fine-tuning**: continuing to train a pretrained model on new data.
- **mAP@50 / AP@50**: average precision over confidence levels, counting a
  box as correct when it overlaps a labelled box by at least 50% IoU. mAP
  averages AP over classes; with one class they describe the same thing.
- **mAP@50:95**: the same averaged over stricter IoU cutoffs from 50% to 95%,
  so it also rewards tight boxes.
- **Data leakage**: evaluation data that is too similar to training data, so
  scores look better than they would on genuinely new input.
- **Generalization**: how well a model does on data unlike what it was
  trained on.
- **Workflow**: a Roboflow pipeline of blocks (input, model, visualizations,
  outputs) that can be run and published.
- **Deployable model ID**: the fully qualified identifier a Workflow uses to
  load a trained model, as opposed to its display name.

## Problems I Hit

1. **Auto Label boxed officials and non-players** in the preview.
2. **The version builder showed `Unannotated: 56`** while the dataset had
   annotations.
3. **Stretch to 512x512 distorted the wide footage.**
4. **High same-clip metrics couldn't show generalization**, because
   validation and test came from the training clip.
5. **On the unseen image, no threshold was clean.** An obvious player was
   missed at 0.50 and 0.40; recovering them at 0.30 added roughly four
   sideline/non-player boxes.
6. **The Agent-built Workflow failed on its first run** with an invalid
   model ID in `detect_players`.

## How I Solved Them

1. Kept Auto Label, but reviewed every image against the policy: removed
   official and sideline boxes, added missed players, fixed duplicate and
   loose boxes.
2. Opened the Train, Valid and Test image views and confirmed the boxes were
   attached before creating the version. Treated the counter as a UI
   inconsistency, not as missing labels.
3. Used Fit (black edges) in 512x512 instead.
4. Tested the trained model on an image from a different match, kept out of
   the dataset, and documented every metric with its sample size and the
   same-clip caveat.
5. Didn't pick a winner. Recorded what each threshold gained and cost; the
   right choice depends on whether a missed player or a box on a non-player
   costs more. More diverse training data is listed as the next step.
6. Asked the Agent to investigate only the failing block. It took the
   deployable ID from the model picker, changed only `model_id`, and the
   rerun succeeded before the Workflow was published.

## What I Would Explain to a Customer

The local project finds every person in the footage, because the pretrained
model only knows "person". To find rugby players specifically, we defined a
`rugby player` class with clear rules (players yes; referees, touch judges,
spectators and staff no), labelled 56 frames with Auto Label plus a manual
check of every image, and trained a small RF-DETR model on Roboflow.

On images from the same clip it scored well: 86.7% mAP@50 on validation, with
93.2% precision and 77.9% recall. Those images are close relatives of the
training images, so this is a baseline, not a guarantee.

On a photo from a different match, it found most players but missed an
obvious one at the 0.50 setting. Lowering the setting to 0.30 recovered that
player but added boxes on sideline people. No setting fixed both, so the
next step we'd suggest is more varied training data, especially other games
and more officials, rather than more threshold tuning.

We also packaged the model as a Workflow that returns an annotated image and
the raw detections. Its first run failed because the model was referenced by
its display name; using the ID from the model picker fixed it.

## Remaining Questions

*Future work, not implemented in this PR:*

- How much does footage from several games improve the unseen-match result?
- Would including more officials (left unlabelled) reduce the non-player
  boxes on new footage?
- What would a truly independent test set, from games not used for
  training, show for mAP@50 and recall?
- Does augmentation help once the data is more diverse, compared against
  `v1-baseline`?
- Would a larger model size change anything that better data doesn't?
- Could the custom detector feed the local ByteTrack pipeline, and would
  tracking a `rugby player` class behave differently from tracking `person`?
