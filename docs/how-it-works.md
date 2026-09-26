# How It Works

This page explains what happens between a rugby video going in and an
annotated video coming out. It starts with the ideas, then shows which tool
and which part of the project handles each one. No computer vision background
is assumed.

To run the commands, see [Getting started](getting-started.md).

## The pipeline at a glance

```text
video
  → frame reading          split the video into individual pictures
  → RF-DETR detection      find objects in each picture
  → sv.Detections          store what was found in a standard format
  → person filtering       keep only people
  → ByteTrack tracking     link the same person across pictures
  → Supervision annotation draw boxes and labels
  → output                 save an image or a video
```

The single-frame command (`rugby_vision.detection`) runs the steps up to
annotation on one picture and saves an image. The full-video command
(`rugby_vision.tracking`) runs every step on every picture and saves a video.

## Terms used on this page

- **Frame:** one still picture from a video. The project's clip has 1091 of
  them, about 55 per second.
- **Bounding box:** a rectangle around an object, stored as the pixel
  coordinates of its top-left and bottom-right corners.
- **Detection:** one thing the model found: a bounding box, what kind of
  object it is (its *class*, such as `person`), and a confidence score.
- **Confidence:** a number from 0 to 1 showing how sure the model is about a
  detection. A **threshold** is the minimum confidence a detection needs to be
  kept.
- **Pretrained model:** a model someone else has already trained. This
  project uses it as-is and doesn't train anything.
- **Track:** the tracker's record of one object followed over time. Each
  confirmed track gets a number, its **tracker ID**.

## Each stage

### 1. Frame reading

A video file is a compressed sequence of frames. Before a model can look at
anything, the frames have to be decoded back into pictures.

Two details matter here:

- **Colour order.** OpenCV, the library that decodes the video, stores
  colours as blue-green-red (BGR). RF-DETR expects red-green-blue (RGB), so
  each frame is converted before detection. Drawing and saving use the
  original BGR frame, because that's what OpenCV writes.
- **Exact frames.** Jumping straight to "frame 545" in a compressed video
  can quietly return a nearby frame instead. This happened with the
  project's clip, so the project decodes frames in order to land on the exact
  one. The full story is in the
  [PR 007 learning note](learnings/PR-007-exact-frame-reading.md).

### 2. Detection (RF-DETR)

RF-DETR is an object detection model. Given one picture, it answers two
questions: *what* objects are there, and *where* are they?

This project uses **RF-DETR Nano**, the smallest version, with weights
pretrained on COCO, a large public dataset of everyday objects. COCO includes
a general `person` class but nothing rugby-specific, so the model can't tell
a player from a referee or a spectator.

**RF-DETR detects; it does not track.** It looks at each frame on its own and
has no memory of earlier frames. On frame 100 and frame 101 it might find the
same eleven people, but it has no idea they're the same people.

### 3. `sv.Detections`

RF-DETR returns its results as an `sv.Detections` object. This is
Supervision's standard container for everything found in one frame: the boxes,
confidences and classes, plus room for extra information such as class names
and, later, tracker IDs.

Because RF-DETR, ByteTrack and Supervision's drawing tools all use this same
container, results pass straight from one to the next with no conversion code.

### 4. Person filtering

The model can report any COCO class, such as `sports ball` or `chair`. The
project keeps only detections whose class name is `person` and drops the
rest.

It filters by the class *name* rather than the class *number*, because in
this model's numbering `person` is 1, not 0, and matching on the name avoids
that mistake.

### 5. Confidence threshold

The threshold is set when RF-DETR runs, and it controls a tradeoff:

- A **lower** threshold keeps more detections. It finds more of the real
  people, but also lets in more mistakes, such as a bag or a duplicate box.
- A **higher** threshold keeps only confident detections. There are fewer
  mistakes, but more real people are missed.

The commands default to 0.5. The project's evaluation measured this tradeoff
at 0.20, 0.40 and 0.60 (see
[How evaluation fits in](#how-evaluation-fits-in)).

### 6. Tracking (ByteTrack)

Tracking answers the question detection can't: *which person in this frame
is the same person from the last frame?*

ByteTrack takes each frame's detections and matches them to the tracks it is
already following. It uses where each box is and where it expects it to move
next. A match continues the track and keeps its ID. A detection that matches
nothing may start a new track.

**ByteTrack tracks; it does not detect.** It never looks at the picture. It
only sees the boxes RF-DETR gives it, so a person RF-DETR misses can't be
tracked.

Things to know when reading the output:

- **Confirmation takes time.** A new track has to be matched on consecutive
  frames before ByteTrack confirms it and gives it an ID. Until then it is
  reported with the placeholder ID −1, and the project draws it in grey as
  `unconfirmed`.
- **An ID is not a player identity.** ByteTrack matches boxes by position and
  motion, not by what the person looks like. When players overlap, or the
  camera pans quickly, an ID can jump to a different person. A person who is
  lost and found again gets a new ID. On the project's clip, 44 track IDs were
  confirmed, far more than the number of people visible at any moment.
- **Frame rate matters.** ByteTrack measures how long to keep a lost track in
  frames, assuming 30 frames per second unless told otherwise. The project
  passes the video's real frame rate so that time stays correct.

The [PR 005 learning note](learnings/PR-005-video-tracking.md) walks through
real examples of these effects in the project's footage.

### 7. Annotation (Supervision)

Supervision's annotators draw the results onto the frame: a box for each
detection, plus a label.

- In single-frame detection, the label is the class and confidence, such as
  `person 0.87`.
- In tracking, a confirmed track shows its ID and confidence, such as
  `#7 0.87`, in a colour that stays the same for that ID. Unconfirmed
  detections are grey and labelled `unconfirmed 0.66`.

**Annotators only draw.** They don't find anything themselves. If RF-DETR
returns no detections, there's nothing to draw.

### 8. Output

- The single-frame command saves a JPEG image with OpenCV.
- The tracking command writes each annotated frame into an MP4 with
  Supervision's `VideoSink`. The video has the same size, frame rate and
  frame count as the source.

All output goes to `outputs/`, which git ignores.

## Who does what

| Tool | Responsible for | Not responsible for |
| --- | --- | --- |
| **RF-DETR** (`rfdetr`) | Finding objects in a single picture and scoring its confidence | Remembering anything between frames |
| **ByteTrack** (`trackers`) | Linking detections across frames and assigning tracker IDs | Finding objects, or knowing who a person is |
| **Supervision** (`supervision`) | The shared `sv.Detections` format, drawing boxes and labels, reading video details, and writing the output video | Detecting or tracking |
| **OpenCV** (`cv2`) | Decoding frames, BGR/RGB conversion, and saving images | Understanding what is in the picture |

And where each stage lives in the project:

| Stage | Module |
| --- | --- |
| Frame reading, detection, person filtering, single-frame annotation | `src/rugby_vision/detection.py` |
| Full-video loop, tracking, track annotation, video output | `src/rugby_vision/tracking.py` (reuses the person filter from `detection.py`) |
| Evaluation images, review CSV, metrics | `src/rugby_vision/evaluation.py` |

## How evaluation fits in

The pipeline produces boxes, but how good are they? The evaluation answers
that for this footage with a person in the loop:

1. `evaluation generate` runs detection on 20 fixed frames at three
   thresholds and saves the images.
2. A reviewer looks at each image and counts correct boxes, wrong boxes and
   missed people. The code never decides what counts as correct.
3. `evaluation summarize` checks the counts for consistency and turns them
   into **precision** (how many boxes were real people) and **recall** (how
   many real people got a box).

The completed review is committed, so its results can be viewed without a
video. See [Commands](commands.md#evaluation-summarize) for the output, and
the [PR 006 learning note](learnings/PR-006-detection-evaluation.md) for the
review rules and what the results show.
