# Hosted Roboflow Experiment

The rest of Rugby Vision runs locally: a pretrained RF-DETR model finds
people and ByteTrack follows them. This page describes a separate experiment
on Roboflow's hosted platform, where a small rugby-specific dataset was built,
a custom model was trained on it, and the model was published as a Workflow.

The experiment changed no code in this repository. The dataset, the trained
model and the Workflow live in a Roboflow workspace, not in git.

## Goal

The local pipeline uses a pretrained model with COCO's generic `person`
class. It can't tell a player from a referee, a touch judge or a spectator;
they are all `person` (see [Detection](detection.md#class)).

This experiment asks what changes when the problem becomes:

> Detect rugby players specifically.

That means defining a class of our own, labelling data for it, training a
model, and checking whether the result holds up beyond the footage it was
trained on.

It is a small platform-learning experiment, not a production-grade rugby
detector. The dataset is 56 images from one short clip.

## Hosted pipeline

```text
video
  → sampled frames
  → Auto Label
  → manual review
  → dataset
  → version (v1-baseline)
  → RF-DETR Small training
  → evaluation
  → unseen-image inference
  → Workflow
```

## Dataset creation

### Source

- The source was the project's own rugby clip, about 20 seconds long.
- It was sampled at roughly 3 frames per second.
- 56 reviewed gameplay images were used.
- All of them come from one short clip, so neighbouring frames are highly
  correlated: the same match, camera, players and lighting, sampled about a
  third of a second apart.

### One class and an annotation policy

The project has one class, `rugby player`. Before labelling, the policy was
written down.

**Label:**

- active rugby players on the field
- clearly identifiable partially occluded players
- clearly identifiable cropped players
- clearly identifiable distant players

**Don't label:**

- referees
- touch judges
- spectators
- sideline staff
- camera crew
- equipment and flags
- ambiguous body fragments

### How this differs from the local review

The local [evaluation](evaluation.md#the-review-policy) counted every person
as ground truth, including referees, touch judges and spectators, because the
pretrained model's class is `person`. A box on a referee was correct there.

Here the same box is a mistake. The class definition, not the model, decides
what counts as right. A product-specific class only works if everyone
labelling the data applies the same definition.

### Auto Label and manual review

The images were labelled with Roboflow's Auto Label, using the
**GPT-6 Astra (Boxes)** model with the class prompt `rugby player`.

- The preview worked well overall, but mislabelled some officials and other
  non-players as players.
- The full batch was then auto-labelled.
- **Every generated image was reviewed by hand:**
  - false-positive boxes on officials and sideline people were removed;
  - missed players could be added;
  - duplicate and loose boxes were corrected where needed.

Auto Label made annotation faster. It didn't remove the need for an
annotation policy or for manual quality checks: the mistakes seen in the
preview were exactly the distinction the class exists to make.

### Split

| Split | Images |
| --- | --- |
| Train | 42 |
| Validation | 9 |
| Test | 5 |
| **Total** | **56** |

Because every image comes from the same short clip, the validation and test
images are close relatives of the training images. This is a **same-clip
baseline**. Validation and test results show how well the model learned this
clip, not how well it generalizes to other games.

## Dataset version

A version freezes the dataset together with its preprocessing and
augmentation settings, so a training run can be traced back to exactly what
it saw.

| Setting | Value |
| --- | --- |
| Name | `v1-baseline` |
| Auto-Orient | Enabled |
| Resize | Fit (black edges) in 512x512 |
| Augmentation | None |

**Fit instead of Stretch.** Stretch to 512x512 was rejected because it
visibly distorted the wide rugby footage. Fit (black edges) in 512x512
preserved the wide source aspect ratio by padding rather than stretching.

**No augmentation.** The goal of `v1-baseline` was a clean reference point.
Adding augmentation at the same time as everything else would make it
impossible to tell later which change helped or hurt. Augmentation,
hyperparameters and data can each be changed against this baseline, one at a
time.

**A status inconsistency.** While the version was being built, the builder
showed `Unannotated: 56`, which contradicted the dataset state. The Train,
Valid and Test image views were checked before creating the version, and the
bounding-box annotations were attached to the images. This was treated as a
UI/status inconsistency, not as evidence of missing labels.

## Hosted training

| Setting | Value |
| --- | --- |
| Engine | Custom Training |
| Architecture | Roboflow RF-DETR |
| Model size | Small |
| Dataset version | `v1-baseline` |
| Checkpoint | Default |
| Hyperparameters | Default |
| Augmentation | None |
| Credit cap | 1.00 |
| Credits used | 0.44 |

Training completed successfully. The default training recipe allowed up to
100 epochs; this run ended around epoch 46.

### Results

| Metric | Validation result |
| --- | --- |
| mAP@50 | 86.7% |
| Precision | 93.2% |
| Recall | 77.9% |
| F1 | 84.9% |

- **Test-set AP@50** for `rugby player`: **92.0%**.
- The training graph showed mAP@50:95 around the low-50% range. An exact
  value wasn't recorded.

**Read these numbers cautiously:**

- the validation set is 9 images and the test set is 5;
- all of them come from the same short clip as the training images;
- neighbouring frames are highly correlated;
- so they are **not evidence that the model works on other games**.

They are useful as a baseline to compare later versions against.

### What the validation metrics suggest

Validation precision (93.2%) was higher than recall (77.9%). On these images
the model was relatively conservative: most boxes it drew were correct, while
some players were missed. That's the same kind of tradeoff the local
[evaluation](evaluation.md#the-confidence-threshold-tradeoff) measured at
higher thresholds.

## External generalization check

Same-clip metrics can't show how the model behaves on footage it has never
seen, so it was tried on one image from a **different rugby match**.

The image differed in uniforms, camera position, field, lighting and scene
composition, including different spectators and sideline people. It was used
for inference only and was **not** added to the training dataset.

The same image was run at three confidence thresholds:

| Threshold | Detections | Player recovery | Observed false positives |
| --- | --- | --- | --- |
| 0.50 | 24 | Most obvious players detected; at least one obvious player missed | Fewer low-confidence sideline false positives visible; some officials and non-player people still a concern |
| 0.40 | 25 | The missed player was still missed | One additional sideline/non-player false positive |
| 0.30 | 29 | The missed player was recovered | Roughly four additional sideline/non-player detections |

None of these is universally best. Which one fits depends on whether a missed
player or a box on a non-player costs more.

**The confidence ranges overlap.** Lowering the threshold from 0.50 to 0.30
brought back the missed player, but only together with several sideline
detections. In this image, the missed player and those non-players scored in
the same range, so none of the three thresholds kept one and dropped the
other. A threshold can only
cut along confidence; when correct and incorrect detections share a
confidence range, it can't separate them.

This reproduced, on an unseen match, the precision/recall tradeoff from the
local [evaluation](evaluation.md#the-confidence-threshold-tradeoff): a lower
threshold can improve recall while introducing false positives.

Formal precision and recall were **not** calculated for this image. No
full ground-truth annotation was made for it, so the observations above are
qualitative.

## Workflow

After training, a simple Roboflow Workflow was built around the model:

```text
Inputs.image
  → Object Detection Model   detect_players   (confidence 0.50)
  → Bounding Box Visualization   draw_boxes
  → Label Visualization          draw_labels
  → Outputs: output_image, predictions
```

It takes an image, runs the trained rugby-player detector, draws boxes and
labels, and returns both the annotated image and the raw predictions.

### Building it with the Roboflow Agent

The Workflow was deliberately built with the Roboflow Agent.

1. The Agent generated the Workflow structure successfully.
2. The first run failed in `detect_players` with an invalid model ID / model
   identifier format error.
3. The Agent had referenced the model by a short display identifier, not by
   a deployable model ID.
4. The Agent was asked to investigate only the failing block, not to
   redesign the Workflow.
5. It inspected the workspace model picker and found the fully qualified
   deployable model ID, of the form:

   ```text
   <workspace>/rugby-player-detection-1nown-1-rfdetr-small-t1
   ```

6. It changed only `detect_players.model_id`. The input, the 0.50 threshold,
   both visualization blocks and both outputs were left unchanged.
7. The rerun on the unseen-match image succeeded. It returned the annotated
   image and the raw predictions, with 24 `rugby player` detections at 0.50,
   the same count as the manual test at that threshold.
8. The Workflow was published.

The Agent made construction faster, but the configuration it generated still
had to be inspected, diagnosed and validated. The useful debugging steps
were: read the error, find the one block it names, fix only that block, and
rerun on a known image to confirm the result.

**Use identifiers from the workspace or the model picker rather than typing
or guessing model IDs.** A display name that looks right in the interface
isn't necessarily the ID the Workflow runtime expects.

## Local vs hosted

The two halves of the project answer different questions. Neither is better
in general.

| | Local (Days 1–3) | Hosted (Day 4) |
| --- | --- | --- |
| Question | Find and follow every person in the clip | Detect rugby players specifically |
| Model | Pretrained RF-DETR Nano | RF-DETR Small fine-tuned on Roboflow |
| Class | Generic COCO `person` | Custom `rugby player` |
| Training data | None; pretrained weights used as-is | 56-image dataset with Auto Label and manual review |
| Runs on | Local CUDA GPU | Roboflow's hosted platform |
| Tracking | ByteTrack | None |
| Evaluation | Manual count review at 0.20/0.40/0.60 on 20 frames | Hosted metrics on 9 validation / 5 test images, plus a qualitative external check |
| Output | Annotated image and tracked video | Published Workflow returning an annotated image and predictions |
| Training | None | Hosted fine-tuning |

## Limitations

- **Tiny dataset:** 56 images.
- **One short training clip.**
- **Correlated frames** across train, validation and test.
- **Only one class.**
- **Officials can still be confused with players** on unseen footage.
- **No formal ground truth for the external image**, so no precision or
  recall on it.
- **No second-game training data.**
- **No v2 or augmentation comparison.** Only `v1-baseline` was trained.
- **No production deployment benchmark:** latency, throughput and cost at
  scale weren't measured.

## What I would do next

*Future work, not implemented:*

- Add footage from multiple games.
- Deliberately include diverse officials in the images, left unlabelled, so
  the model sees them as negative context.
- Create a truly independent test set from games not used for training.
- Consider augmentation after improving data diversity, and compare it
  against `v1-baseline`.
- Compare model sizes or architectures only after the data is better.
- Test tracking or custom player identity separately, if a use case needs
  them.

## Related

- [Detection](detection.md): the generic `person` class and the confidence
  threshold
- [Evaluation](evaluation.md): the local precision/recall review
- [Demo](demo.md#optional-hosted-roboflow-extension-23-min): presenting this
  experiment
- [PR 013 learning note](learnings/PR-013-hosted-roboflow.md): what was
  learned along the way
