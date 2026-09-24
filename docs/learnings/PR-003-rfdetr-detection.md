# PR 003 - RF-DETR Single-Frame Person Detection

## What I Built

A single-frame detection smoke test in `src/rugby_vision/detection.py`:

```text
data/raw/rugby.mp4
     ↓  OpenCV reads the middle frame (BGR)
     ↓  convert BGR → RGB
RFDETRNano.predict(threshold=0.5)
     ↓  sv.Detections (xyxy, confidence, class_id, data["class_name"])
filter on class_name == "person"
     ↓
sv.BoxAnnotator + sv.LabelAnnotator ("person 0.87")
     ↓
outputs/detection-smoke-test.jpg
```

Run it with:

```bash
uv run python -m rugby_vision.detection
```

Optional flags: `--video`, `--frame-index`, `--threshold`, `--output`.

I also added a `uv_build` build-system to `pyproject.toml` so the `src/`
package can be imported, and pytest tests for frame reading, person
filtering, and label formatting that don't need the model or a GPU.

Observed result on `data/raw/rugby.mp4` (832x384, 1091 frames, ~55.18 fps):

```text
Frame:       545 of 1091 (9.88s at 55.18 fps)
Threshold:   0.5
Device:      cuda (NVIDIA GeForce RTX 4080 SUPER)
Detections:  11 total, classes: person
People:      11 retained
Confidences: 0.90, 0.88, 0.86, 0.85, 0.80, 0.79, 0.79, 0.69, 0.68, 0.66, 0.65
Output:      outputs/detection-smoke-test.jpg (832x384)
```

Running it a second time gave identical counts and confidences.

## What I Learned

- `predict()` returns an `sv.Detections` directly, so no conversion code
  was needed between RF-DETR and Supervision.
- RF-DETR's `predict()` docstring says images should be **RGB**. OpenCV
  reads **BGR**, so the frame is converted before inference. The annotators
  draw on the original BGR frame because `cv2.imwrite` expects BGR.
- The pretrained COCO checkpoint returns **sparse COCO category IDs
  (1–90)**, where person is `1`, not `0`. RF-DETR also puts a readable
  name in `detections.data["class_name"]`. Filtering on the name avoids
  guessing which numeric ID means "person".
- Filtering uses a boolean mask: `detections[class_names == "person"]`
  keeps the rows that match.
- RF-DETR moves model weights to the GPU **lazily**. Right after
  `RFDETRNano()` is constructed, the weights reported `cpu`. After
  `predict()` they reported `cuda:0`. So `torch.cuda.is_available()` alone
  doesn't prove the model ran on the GPU; the script now reads
  `model.model.device` after `predict()`.
- Annotators only draw the detections they are given. They don't detect
  anything.

### Manual review of the annotated frame

- I inspected `outputs/detection-smoke-test.jpg` by eye.
- I estimate roughly 13 visible or partially visible people in the frame;
  RF-DETR returned 11 person detections at threshold 0.5.
- The hardest area is the dense ruck/maul, where players overlap and
  partially block each other.
- Some partially visible or cropped people still received a person box.
- The logo overlay, black borders, and field markings did not create
  obvious false positives in this frame.
- Counting ground truth by hand is somewhat ambiguous when only small body
  parts are visible or players are heavily occluded, so "roughly 13" is an
  estimate, not an exact label.
- Running the same frame at threshold 0.7 dropped the detections from 11
  to 7. That matches the original run: four of the confidence scores
  (0.69, 0.68, 0.66, 0.65) were below 0.70.

## Important Terms

- **Inference**: running an already-trained model on new input. No
  training happened here.
- **Confidence threshold**: `predict(threshold=0.5)` drops detections
  scoring below 0.5.
- **`sv.Detections`**: Supervision's standard container for one frame's
  boxes (`xyxy`), `confidence`, `class_id`, and extra `data`.
- **BGR vs RGB**: the order of the color channels. OpenCV uses BGR; most
  models, including RF-DETR, expect RGB.
- **COCO category ID**: the numeric class IDs from the COCO dataset. They
  are sparse (some numbers are unused) and start at 1.

## Problems I Hit

1. **`src/` package not importable.** `pyproject.toml` had no
   build-system, so uv treated the project as "virtual" and
   `python -m rugby_vision.detection` could not find the package.
2. **Misleading device report.** The first version printed the GPU name
   whenever `torch.cuda.is_available()` was true. When I checked the
   weights right after constructing the model, they were on `cpu`, so that
   message didn't prove anything about where inference ran.
3. **`ruff format --check .` fails on the existing study notes.** Ruff
   0.16 also formats Python code blocks inside Markdown, and
   `docs/rf-oss-study-notes.md` would be reformatted. The same failure
   happens without this PR's changes.
4. **The person filter removed nothing on this frame.** All 11 detections
   at threshold 0.5 were already `person`, so the real run didn't show the
   filter in action. The unit tests cover mixed classes.

## How I Solved Them

1. Added `[build-system]` with the `uv_build` backend (uv 0.9.10 is
   installed). `uv sync` then installed the project in editable mode, and
   `uv.lock` changed one line (`virtual` → `editable`).
2. Read RF-DETR's source: `predict()` is wrapped by
   `_ensure_model_on_device`, which moves the weights on first use. I now
   report `model.model.device` after `predict()` and confirmed separately
   that the weights were on `cuda:0` after a `predict()` call.
3. Ran `ruff format --check` on the Python files only (`src`, `tests`,
   `main.py`), and they pass. I left the study notes unchanged because
   they're outside this PR's scope.
4. Added unit tests with hand-built `sv.Detections` that mix `person`,
   `sports ball`, and `chair`.

## Model Weights: General Behavior vs This PR

- **General RF-DETR behavior:** on first use, `RFDETRNano()` downloads the
  pretrained Nano checkpoint and caches it locally.
- **What happened in this PR:** the weights were already cached at
  `~/.roboflow/models/rf-detr-nano.pth` from an earlier smoke test. The log
  said `File ... already exists with correct MD5 hash.`, so nothing was
  downloaded.

RF-DETR also logged some messages that didn't stop the run:

- DINOv2 backbone weights were not loaded because of the patch size and
  positional encodings. The message says this is expected when loading a
  pretrained RF-DETR checkpoint.
- `Model is not optimized for inference`, with a suggestion to call
  `model.inference(dtype=torch.float16)`. I didn't do this because speed
  isn't the goal of a single-frame smoke test.

## What I Would Explain to a Customer

We took one frame from the rugby clip and ran Roboflow's smallest
pretrained RF-DETR model on it. With no rugby-specific training, it found
11 people with confidence between 0.65 and 0.90, out of roughly 13 visible
by eye. We saved an image with a box and score on each detection so the
result can be checked visually. Most misses are in the dense ruck/maul,
where players block each other. This confirms the footage and model work
together before we process full video or add tracking.

## Remaining Questions

- The ruck/maul is where people seem to be missed. Would a threshold
  below 0.5 recover them, and how many false positives would it add?
- How should ground truth be defined for heavily occluded or barely
  visible players before we do any formal evaluation?
- The logo overlay, black borders, and field markings caused no obvious
  false positives on this frame. Does that hold on other frames?
- How much faster would FP16 inference (`model.inference(...)`) be when we
  process the full video?
