# Roboflow Open-Source Ecosystem Study Notes

These notes explain the main Roboflow open-source projects relevant to a local sports computer-vision project:

* `roboflow/rf-detr`
* `roboflow/supervision`
* `roboflow/trackers`
* `roboflow/notebooks`
* `roboflow/sports`

The main relationship to remember is:

```text
Video / Image
     ↓
RF-DETR
detects objects
     ↓
sv.Detections
standard representation
     ↓
Roboflow Trackers
associates objects across frames
     ↓
Supervision Annotators
draw boxes, labels, traces, zones
     ↓
Annotated Output
```

---

# 1. `roboflow/rf-detr`

## What problem does RF-DETR solve?

RF-DETR is Roboflow's transformer-based computer-vision model family.

For this project, the important capability is **object detection**.

Object detection answers two questions:

1. What object is present?
2. Where is the object in the image?

For example:

```text
Input frame
     ↓
RF-DETR
     ↓
person — confidence 0.91 — box [x1, y1, x2, y2]
person — confidence 0.83 — box [x1, y1, x2, y2]
person — confidence 0.72 — box [x1, y1, x2, y2]
```

RF-DETR currently has multiple model sizes including Nano, Small, Medium, and Large. The core pretrained detection models are trained on Microsoft COCO, which contains common object classes including `person`.

For Rugby Vision, we care primarily about:

```python
RFDETRNano
```

because we want a relatively lightweight model while learning.

---

## How is RF-DETR installed?

The basic package can be installed with:

```bash
pip install rfdetr
```

or with `uv`:

```bash
uv add rfdetr
```

If training a model locally, RF-DETR currently separates the additional training dependencies:

```bash
pip install "rfdetr[train]"
```

The base package is sufficient when we only want to run pretrained inference.

---

## How is inference performed?

A simplified example is:

```python
from rfdetr import RFDETRNano

model = RFDETRNano()

detections = model.predict(
    image,
    threshold=0.5
)
```

The important part is:

```python
model.predict(...)
```

This performs **inference**.

Inference means:

> Give an already-trained model new input and ask it to make predictions.

RF-DETR's `predict()` method currently returns a Supervision `Detections` object directly.

Conceptually:

```text
image
  ↓
RF-DETR pretrained weights
  ↓
model.predict()
  ↓
sv.Detections
```

For a video, this happens frame by frame:

```text
frame 1 → predict
frame 2 → predict
frame 3 → predict
frame 4 → predict
...
```

---

## What does the confidence threshold mean?

For example:

```python
model.predict(image, threshold=0.5)
```

means:

> Only return detections whose prediction confidence passes the specified threshold.

A lower threshold generally allows more predictions through.

A higher threshold generally requires stronger predictions.

For example:

```text
threshold = 0.20

person 0.91 ✓
person 0.72 ✓
person 0.55 ✓
person 0.31 ✓
person 0.18 ✗
```

versus:

```text
threshold = 0.60

person 0.91 ✓
person 0.72 ✓
person 0.55 ✗
person 0.31 ✗
person 0.18 ✗
```

This eventually becomes important when discussing **precision and recall**.

---

## How is RF-DETR trained?

Training is different from inference.

Inference:

```text
trained model
     +
new image
     ↓
prediction
```

Training:

```text
labeled dataset
     ↓
model learns patterns
     ↓
updated model weights
```

RF-DETR currently supports datasets in COCO and YOLO formats. A basic training workflow looks like:

```python
from rfdetr import RFDETRMedium

model = RFDETRMedium()

model.train(
    dataset_dir="path/to/dataset",
    epochs=100,
    batch_size="auto",
    output_dir="output",
)
```

RF-DETR also exposes a more customizable PyTorch Lightning training path, but that is more advanced than we need initially.

---

## Where does RF-DETR fit in Rugby Vision?

Directly.

```text
rugby frame
     ↓
RF-DETR
     ↓
detect people
```

RF-DETR is our **detector**.

It does not track the players.

It does not draw boxes.

It does not understand rugby rules.

It produces detections.

---

## APIs/classes I should recognize

At minimum:

```python
from rfdetr import RFDETRNano

model = RFDETRNano()

detections = model.predict(
    image,
    threshold=0.5
)
```

Important names:

```text
RFDETRNano
RFDETRSmall
RFDETRMedium
RFDETRLarge

model.predict()
model.train()
```

---

## What should I be able to explain in an interview?

I should be able to say:

> RF-DETR is Roboflow's real-time transformer-based computer-vision model family. In my project, I used a pretrained RF-DETR model for person detection. I wasn't initially training a rugby-specific model; I was performing inference using pretrained weights. RF-DETR returned bounding boxes, classes, and confidence scores that I could then pass into tracking and visualization components.

---

# 2. `roboflow/supervision`

## What problem does Supervision solve?

Supervision is a model-agnostic computer-vision toolkit.

It provides reusable building blocks around ML models so developers don't have to repeatedly implement things like:

```text
detection data structures
bounding-box drawing
labels
video reading
video writing
traces
zones
dataset utilities
```

Roboflow describes Supervision as a toolkit providing building blocks from data loading through real-time zone counting.

The important distinction is:

```text
RF-DETR = model

Supervision = tools around model output
```

---

# What is `sv.Detections`?

`sv.Detections` is a standardized data structure for representing object detections.

Think of it as:

```text
one object that contains everything we know
about detections in one frame
```

Current fields include:

```text
xyxy
mask
confidence
class_id
tracker_id
data
metadata
```

The most important ones for us are:

### `xyxy`

Bounding-box coordinates:

```text
[x1, y1, x2, y2]
```

For example:

```text
[120, 80, 210, 300]
```

means approximately:

```text
top-left:
x = 120
y = 80

bottom-right:
x = 210
y = 300
```

### `confidence`

How strongly the detector supports the prediction.

Example:

```text
0.92
```

### `class_id`

Which class the model thinks the object belongs to.

Example:

```text
person
```

might correspond to a particular numeric class ID.

### `tracker_id`

An identity assigned by a tracker.

Example:

```text
tracker_id = 7
```

means:

> The tracker currently believes this detection corresponds to object/track #7.

The official `Detections` object supports bounding boxes, masks, confidence scores, class IDs, tracker IDs, additional data, and metadata.

---

# Why is `sv.Detections` useful?

Because different components can agree on the same data structure.

For our project:

```text
RF-DETR
     ↓
sv.Detections
     ↓
ByteTrack
     ↓
sv.Detections with tracker IDs
     ↓
Supervision Annotators
```

That greatly reduces the amount of conversion code we need.

---

# What annotators exist?

Supervision contains many annotators.

We do not need to memorize all of them.

The most important ones for Rugby Vision are:

### `sv.BoxAnnotator`

Draws bounding boxes.

```python
box_annotator = sv.BoxAnnotator()

frame = box_annotator.annotate(
    scene=frame,
    detections=detections
)
```

### `sv.LabelAnnotator`

Draws text labels.

For example:

```text
person 0.91
```

or after tracking:

```text
ID #7
```

### `sv.TraceAnnotator`

Draws the historical movement path of tracked objects.

Example:

```text
player #7

     •
      \
       •
        \
         •
          \
           ●
```

`TraceAnnotator` requires tracking information because it uses `tracker_id`.

Other annotators include things such as:

```text
RoundBoxAnnotator
BoxCornerAnnotator
MaskAnnotator
DotAnnotator
TriangleAnnotator
RichLabelAnnotator
BlurAnnotator
PixelateAnnotator
BackgroundOverlayAnnotator
```

We don't need all of these.

---

# Does an annotator actually detect anything?

No.

This distinction is extremely important.

```text
RF-DETR
     ↓
finds objects

BoxAnnotator
     ↓
draws the already-found boxes
```

A BoxAnnotator does **not** contain a computer-vision detection model.

If RF-DETR detects nothing:

```text
detections = empty
```

then:

```text
BoxAnnotator
```

has nothing to draw.

---

# What video utilities exist?

The ones most relevant to us are:

### `sv.VideoInfo`

Reads/stores video information such as:

```text
resolution
FPS
frame count
```

### `sv.get_video_frames_generator()`

Reads a video and yields its frames.

Conceptually:

```python
for frame in sv.get_video_frames_generator("rugby.mp4"):
    ...
```

### `sv.VideoSink`

Writes processed frames into an output video.

Conceptually:

```python
with sv.VideoSink(...) as sink:

    for frame in frames:

        ...

        sink.write_frame(annotated_frame)
```

Supervision's current video utilities expose frame generation and a `VideoSink` abstraction around OpenCV video output.

---

# Where does Supervision fit in Rugby Vision?

Directly.

It provides the glue around the detector and tracker.

```text
RF-DETR
     ↓
sv.Detections
     ↓
tracker
     ↓
sv.Detections
     ↓
BoxAnnotator
LabelAnnotator
TraceAnnotator
     ↓
video output
```

---

# APIs/classes I should recognize

```python
import supervision as sv
```

Important classes/functions:

```text
sv.Detections
sv.BoxAnnotator
sv.LabelAnnotator
sv.TraceAnnotator

sv.VideoInfo
sv.VideoSink
sv.get_video_frames_generator
```

Later:

```text
sv.PolygonZone
```

may become useful for field/zone analysis.

---

# What should I be able to explain in an interview?

> Supervision is Roboflow's model-agnostic computer-vision toolkit. I use it as the application layer around my detector. RF-DETR gives me detections, Supervision gives me a standardized `Detections` representation plus video and visualization utilities, and then the tracker can add persistent IDs to those detections.

---

# 3. `roboflow/trackers`

## What problem does Trackers solve?

Detection answers:

> What objects exist in this frame?

Tracking answers:

> Which object in this frame corresponds to which object from earlier frames?

For example:

Without tracking:

```text
FRAME 1

person
person
person


FRAME 2

person
person
person
```

There is no identity.

With tracking:

```text
FRAME 1

person ID 1
person ID 2
person ID 3


FRAME 2

person ID 1
person ID 2
person ID 3
```

The tracker attempts to maintain those identities over time.

Roboflow's Trackers library is designed to take detections from a detector and assign/maintain IDs across video frames.

---

# What trackers currently exist?

Roboflow's current Trackers API includes:

```text
SORT
ByteTrack
OC-SORT
BoT-SORT
C-BIoU
McByte
```

The corresponding classes include:

```python
SORTTracker
ByteTrackTracker
OCSORTTracker
BoTSORTTracker
CBIoUTracker
McByteTracker
```

---

# How does ByteTrack receive detections?

Using the current Roboflow Trackers package:

```python
from trackers import ByteTrackTracker

tracker = ByteTrackTracker()

tracked_detections = tracker.update(detections)
```

Here:

```text
detections
```

is a:

```text
supervision.Detections
```

object.

That means our relationship is extremely straightforward:

```text
RF-DETR
     ↓
sv.Detections
     ↓
ByteTrackTracker.update()
     ↓
sv.Detections
with tracker IDs
```

The Trackers package explicitly supports `supervision.Detections` natively.

---

# What does ByteTrack add?

Before tracking:

```text
xyxy
confidence
class_id
```

After tracking:

```text
xyxy
confidence
class_id
tracker_id
```

The crucial addition is:

```text
tracker_id
```

For example:

```text
Player:
bounding box = [...]
confidence = 0.87
class = person
tracker_id = 7
```

If the tracker sees that same player in subsequent frames, it attempts to keep:

```text
tracker_id = 7
```

---

# Why use ByteTrack?

ByteTrack is a strong general-purpose multi-object tracker.

An important idea behind ByteTrack is that it does not simply discard every lower-confidence detection immediately.

Lower-confidence detections can sometimes still help preserve an existing track, especially when an object is:

```text
partially hidden
blurred
far away
temporarily difficult to detect
```

That makes it useful for crowded scenes.

---

# Why would I choose another tracker?

Different tracking algorithms make different tradeoffs.

## SORT

Useful as a relatively simple baseline.

Think:

```text
simple
fast
easy to reason about
```

---

## ByteTrack

Strong general-purpose tracking-by-detection approach.

A good starting point for our rugby project.

---

## OC-SORT

Another tracking approach designed to improve object association, particularly when motion becomes more difficult or observations are interrupted.

It may be worth comparing if ByteTrack struggles.

---

## BoT-SORT

Especially relevant to sports because Roboflow's implementation supports **camera motion compensation**.

In sports video, the camera often pans:

```text
camera moves right
       ↓
EVERYTHING in image appears to move left
```

A tracker that assumes the camera is stationary may interpret some of this movement incorrectly.

BoT-SORT can compensate for camera movement before performing association. Roboflow explicitly calls out handheld, drone, and sports footage as scenarios where this is useful.

---

## McByte

McByte extends a ByteTrack/BoT-SORT-style approach and can optionally use segmentation-mask information to help resolve ambiguous matches.

That can become interesting when players overlap heavily.

---

# Important distinction: tracker vs detector

The tracker **does not detect objects by itself**.

This is incorrect:

```text
ByteTrack
   ↓
find people
```

This is correct:

```text
RF-DETR
   ↓
find people

ByteTrack
   ↓
associate those detections over time
```

Roboflow's tracker documentation explicitly separates detector responsibility from tracker responsibility.

---

# Where does Trackers fit in Rugby Vision?

Directly.

```text
RF-DETR
     ↓
people detected
     ↓
ByteTrack
     ↓
player IDs
```

---

# APIs/classes I should recognize

Initially:

```python
from trackers import ByteTrackTracker

tracker = ByteTrackTracker()

tracked = tracker.update(detections)
```

I should also recognize:

```text
SORTTracker
OCSORTTracker
BoTSORTTracker
McByteTracker
```

even if I do not use them initially.

---

# What should I be able to explain in an interview?

> RF-DETR detects people independently in each frame, but detections alone don't provide persistent identity. I pass those Supervision detections into ByteTrack, which associates detections across frames and assigns tracker IDs. The rugby footage contains occlusion and camera movement, so I also looked at alternatives such as BoT-SORT, which supports camera-motion compensation.

---

# 4. `roboflow/notebooks`

## What problem does this repository solve?

`roboflow/notebooks` is primarily an educational repository.

It contains runnable computer-vision tutorials covering models and techniques including:

```text
RF-DETR
tracking
segmentation
OCR
sports CV
dataset annotation
fine-tuning
polygon zones
```

Roboflow currently lists dedicated tutorials for RF-DETR with ByteTrack, SORT, OC-SORT, and McByte, plus Football AI and basketball player-tracking examples.

---

# Is this a library used by Rugby Vision?

No.

We use this repository as a **reference**.

We do not need:

```python
import roboflow_notebooks
```

Instead:

```text
Roboflow tutorial
        ↓
understand recommended pattern
        ↓
implement our own smaller version
```

---

# RF-DETR + ByteTrack example

The repository currently contains a notebook named:

```text
how-to-track-objects-with-bytetrack-tracker.ipynb
```

and the main repository identifies it as:

> How to Track Objects with RF-DETR and ByteTrack Tracker.

The underlying pattern is essentially:

```text
load detector
      ↓
load video
      ↓
read frame
      ↓
RF-DETR inference
      ↓
detections
      ↓
ByteTrack
      ↓
tracked detections
      ↓
annotate
      ↓
output
```

This is very close to the architecture we are implementing.

---

# Why not simply copy the notebook?

Because our goal is to understand the pieces.

The useful workflow is:

```text
study Roboflow example
       ↓
understand what each component does
       ↓
implement our own small version
       ↓
run it against our rugby footage
       ↓
observe failures
       ↓
document what happened
```

That gives us practical experience rather than simply demonstrating that we can execute someone else's notebook.

---

# Where does Notebooks fit in Rugby Vision?

Reference only.

```text
roboflow/notebooks
      ↓
learning/reference
      ↓
our implementation
```

---

# APIs/classes I should recognize

The Notebooks repository itself does not give us one main API.

Instead, I should recognize the ecosystem demonstrated by the notebooks:

```text
RF-DETR
Supervision
Trackers
Inference
datasets
fine-tuning
sports CV
```

---

# What should I be able to explain in an interview?

> I used Roboflow's notebooks as a reference for the intended ecosystem and tracking patterns, but I implemented the Rugby Vision pipeline in my own project so that I could understand and troubleshoot each stage instead of simply running an existing notebook.

---

# 5. `roboflow/sports`

## What problem does the Sports repository solve?

This repository explores reusable computer-vision tools for sports analytics.

Unlike RF-DETR, Supervision, and Trackers, it is not currently a normal packaged dependency that we need for the first version of Rugby Vision.

The repository focuses on difficult sports CV problems including:

```text
ball tracking
jersey-number recognition
player tracking
player re-identification
camera calibration
```

Roboflow explicitly calls these out as major sports-computer-vision challenges.

---

# Why is sports computer vision difficult?

## Ball tracking

Balls can be:

```text
small
fast
blurred
partially hidden
only a few pixels wide
```

Rugby has the same issue.

---

## Player tracking

Players frequently overlap.

For rugby:

```text
ruck
maul
scrum
tackle
```

may put several players into nearly the same image region.

The tracker has to determine:

> Which detection belongs to which previous player?

---

## Player re-identification

A player might:

```text
leave frame
     ↓
disappear for 5 seconds
     ↓
return
```

A basic tracker may assign them a completely new ID.

Re-identification attempts to recognize that they are the same person.

---

## Jersey-number recognition

Problems include:

```text
motion blur
players facing away
other players blocking jersey
small text
folded clothing
```

That makes jersey OCR substantially harder than ordinary text recognition.

---

## Camera calibration

Sports cameras move.

If we eventually want statistics such as:

```text
player speed
distance traveled
field location
movement pattern
```

raw pixel coordinates are insufficient.

Example:

```text
player moves 200 pixels
```

does NOT automatically mean:

```text
player moved 10 meters
```

Camera calibration attempts to map image-space coordinates onto the real playing surface.

Roboflow's Sports repository identifies dynamic camera angles as one of the major difficulties when extracting advanced spatial statistics.

---

# How does this apply to rugby?

Almost directly.

Soccer problem:

```text
player tracking
```

Rugby equivalent:

```text
rugby player tracking
```

Soccer:

```text
ball tracking
```

Rugby:

```text
rugby ball tracking
```

Soccer:

```text
pitch calibration
```

Rugby:

```text
rugby pitch calibration
```

Soccer:

```text
player re-identification
```

Rugby:

```text
player re-identification
```

Rugby may be even more challenging in certain situations because players intentionally form extremely dense groups:

```text
scrums
rucks
mauls
tackle situations
```

which create severe occlusion.

---

# Are we using `roboflow/sports` directly?

Initially:

```text
NO — reference only
```

It helps us understand:

```text
what difficult sports CV problems look like
what more advanced systems might require
where our simple tracker will eventually fail
```

The repository currently says it does not have a normal Python package release and documents installation directly from GitHub source when someone wants to use its code.

---

# What should I be able to explain in an interview?

> I studied Roboflow Sports because my project operates in the same problem domain. The repository highlights challenges like occlusion, player re-identification, camera calibration, jersey recognition, and ball tracking. I deliberately limited my initial project to person detection and tracking because those more advanced problems require additional models, data, and evaluation.

That explanation also demonstrates good scope control.

---

# Repository Summary

| Repository    | Purpose                                          | Rugby Vision Usage |
| ------------- | ------------------------------------------------ | ------------------ |
| `rf-detr`     | Detection model                                  | **Direct**         |
| `supervision` | Detection structures, video tools, visualization | **Direct**         |
| `trackers`    | Multi-object tracking                            | **Direct**         |
| `notebooks`   | Tutorials/examples                               | **Reference**      |
| `sports`      | Sports-specific CV research/tools                | **Reference**      |

The most important relationship is:

```text
RF-DETR
"What objects exist?"

     ↓

Supervision Detections
"How do we represent those predictions?"

     ↓

Trackers
"Which object is which over time?"

     ↓

Supervision Annotators
"How do we visualize the result?"
```

---

# Knowledge Check — Questions and Answers

## 1. What is the difference between object detection and object tracking?

### Answer

**Object detection** identifies objects independently in an image or video frame.

For example:

```text
Frame 1:

person
person
person
```

It tells us:

```text
what the object is
where it is
how confident the model is
```

But it does not inherently tell us whether a person in Frame 1 is the same person in Frame 2.

**Object tracking** takes detections across multiple frames and tries to maintain identity.

```text
Frame 1:

person ID 1
person ID 2

Frame 2:

person ID 1
person ID 2
```

So:

```text
Detection:
Where are the people right now?

Tracking:
Which person is which over time?
```

---

# 2. When we use `RFDETRNano()` on the rugby video, are we training a new model or performing inference? Explain the difference.

### Answer

We are performing **inference**.

```python
model = RFDETRNano()

detections = model.predict(frame)
```

uses an already-trained model to make predictions on our rugby footage.

We are **not** modifying the model's learned weights.

Inference:

```text
trained model
     +
new rugby frame
     ↓
prediction
```

Training:

```text
labeled images
     ↓
model optimization
     ↓
weights change
     ↓
new/fine-tuned model
```

Our initial Rugby Vision system performs inference.

---

# 3. Why can RF-DETR detect players in the rugby video even though we haven't given it a rugby dataset?

### Answer

Because the pretrained RF-DETR detection models were trained on the Microsoft COCO dataset, which includes the general class:

```text
person
```

We are not initially asking:

> Is this a rugby player?

We are asking:

> Is there a person here?

RF-DETR has already learned visual patterns that help it recognize people.

A rugby player is still visually a person:

```text
head
torso
arms
legs
human proportions
```

Therefore the pretrained model can often detect rugby players without rugby-specific training.

The important limitation is:

```text
RF-DETR knows "person"

not necessarily:

"prop"
"scrum-half"
"wing"
"rugby player"
"referee"
```

A custom rugby dataset could later teach more domain-specific classes.

---

# 4. What information would you expect an `sv.Detections` object to contain? Name at least three things.

### Answer

Important fields include:

```text
xyxy
confidence
class_id
tracker_id
mask
data
metadata
```

At minimum I should remember:

### `xyxy`

Bounding-box coordinates:

```text
[x1, y1, x2, y2]
```

### `confidence`

Model confidence for each detection.

### `class_id`

Predicted object class.

And after tracking:

### `tracker_id`

Persistent track identifier.

---

# 5. What is the difference between `sv.BoxAnnotator` and RF-DETR? Does the annotator actually detect anything?

### Answer

RF-DETR is the **machine-learning model**.

It detects objects.

```text
image
 ↓
RF-DETR
 ↓
detections
```

`sv.BoxAnnotator` is only a visualization tool.

```text
detections
 ↓
BoxAnnotator
 ↓
boxes drawn on image
```

The annotator does not perform detection.

If RF-DETR returns zero detections:

```text
BoxAnnotator
```

has no detections to draw.

So:

```text
RF-DETR = find

BoxAnnotator = draw
```

---

# 6. What does ByteTrack add to the detections that RF-DETR alone doesn't provide?

### Answer

RF-DETR provides detections for individual frames.

For example:

```text
bounding box
class
confidence
```

ByteTrack attempts to associate those detections across frames.

It adds:

```text
tracker_id
```

Conceptually:

Before:

```text
Frame 1: person
Frame 2: person
Frame 3: person
```

After:

```text
Frame 1: person ID 7
Frame 2: person ID 7
Frame 3: person ID 7
```

That means the system can begin reasoning about movement over time.

---

# 7. Suppose player #7 disappears behind three other players during a ruck and comes back as tracker ID #19. What likely happened?

### Answer

The player became **occluded**.

Conceptually:

```text
ID 7 visible
     ↓
player enters ruck
     ↓
RF-DETR cannot reliably see player
     ↓
detection disappears
     ↓
tracker keeps ID 7 alive temporarily
     ↓
track expires or association fails
     ↓
player becomes visible again
     ↓
tracker treats detection as a new object
     ↓
ID 19
```

This is called:

```text
track fragmentation
```

or potentially an:

```text
ID switch / identity-association failure
```

depending on exactly what happened.

The tracker did not suddenly decide that the player's real identity changed.

It lost enough evidence to reliably connect the new detection to the previous track.

This is exactly why dense sports situations like rucks and mauls are difficult.

---

# 8. Why might we eventually consider something like BoT-SORT instead of ByteTrack for sports footage with substantial camera movement?

### Answer

Because the camera itself may move.

Suppose the camera pans rapidly to the right.

Even a player standing still relative to the pitch moves substantially in **image coordinates**.

```text
real world:

player stays approximately here
          ↓

camera pans →

image:

player appears to move ←
```

That camera movement can confuse tracking.

Roboflow's BoT-SORT implementation supports **camera motion compensation**.

It estimates frame-to-frame camera movement and adjusts tracking predictions before object association.

That makes it particularly interesting for:

```text
sports
handheld cameras
drones
panning cameras
```

ByteTrack is still a good first tracker because it keeps our initial system simpler.

---

# 9. Why are we studying `roboflow/notebooks` and `roboflow/sports` without making either one the foundation of our project?

### Answer

Because they serve different purposes.

`roboflow/notebooks` teaches us:

```text
recommended implementation patterns
how Roboflow combines its tools
examples of detection/tracking
```

But simply copying a notebook would teach us less than implementing the pipeline ourselves.

`roboflow/sports` teaches us:

```text
what advanced sports CV problems look like
player tracking
re-identification
ball tracking
camera calibration
jersey recognition
```

But those problems are significantly larger than our initial application.

So:

```text
RF-DETR
Supervision
Trackers

        ↓

BUILD WITH THESE


Notebooks
Sports

        ↓

LEARN FROM THESE
```

This keeps our project small while still exposing us to Roboflow's broader ecosystem.

---

# 10. Explain the entire initial pipeline in plain English, starting with `rugby.mp4` and ending with the annotated output video.

### Answer

We start with:

```text
rugby.mp4
```

The video contains many individual frames.

We read each frame:

```text
rugby.mp4
     ↓
frame 1
frame 2
frame 3
...
```

Each frame is passed to RF-DETR.

```text
frame
 ↓
RF-DETR
```

RF-DETR performs object detection and predicts things such as:

```text
person
bounding box
confidence
```

The results are represented as a Supervision:

```text
sv.Detections
```

object.

So:

```text
frame
 ↓
RF-DETR
 ↓
sv.Detections
```

Because we only care about people, we filter the detections to the person class.

Those detections are then passed to ByteTrack:

```text
sv.Detections
      ↓
ByteTrack
```

ByteTrack compares detections with previous frames and attempts to give each player a persistent:

```text
tracker_id
```

Now we may have something conceptually like:

```text
person
confidence = 0.91
tracker_id = 7
```

Those tracked detections are sent to Supervision annotators.

For example:

```text
BoxAnnotator
LabelAnnotator
TraceAnnotator
```

They draw things like:

```text
bounding box
ID #7
confidence
movement trail
```

onto the original video frame.

The annotated frame is then written to the output video.

This repeats for every frame:

```text
rugby.mp4
     ↓
read frame
     ↓
RF-DETR
     ↓
person detections
     ↓
sv.Detections
     ↓
ByteTrack
     ↓
tracker IDs
     ↓
Supervision annotators
     ↓
annotated frame
     ↓
VideoSink / video writer
     ↓
next frame
```

After all frames have been processed:

```text
rugby.mp4

     ↓

RF-DETR
     ↓
Supervision
     ↓
ByteTrack
     ↓
Supervision Annotators

     ↓

tracked_rugby.mp4
```

The simplest way I should be able to explain it verbally is:

> I read the rugby video frame by frame. RF-DETR detects the people in each frame and returns those predictions as Supervision Detections. ByteTrack then associates those detections across frames to assign persistent tracker IDs. Finally, Supervision draws the bounding boxes, IDs, and other visualizations, and I write each processed frame into a new output video.

---

# Mental Model to Remember

Do not memorize every class and function.

Remember what responsibility belongs to each layer:

```text
RF-DETR
"What can I see?"

        ↓

DETECTION
bounding boxes
classes
confidence

        ↓

Supervision
"How do I represent and work with these results?"

        ↓

Trackers
"Which detection corresponds to which object over time?"

        ↓

TRACKING
tracker IDs

        ↓

Supervision
"How do I visualize and analyze this?"

        ↓

OUTPUT
boxes
labels
traces
zones
video
```

And remember:

```text
Detection ≠ Tracking
Tracking ≠ Detection
Annotation ≠ Detection
Inference ≠ Training
```

Those four distinctions form the foundation of the project.
