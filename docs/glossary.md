# Glossary

Short definitions of the computer vision terms used in Rugby Vision's
documentation. For explanations, see [Detection](detection.md),
[Tracking](tracking.md) and [Evaluation](evaluation.md).

**Annotation**: Drawing results, such as boxes and labels, onto an image or
video. In this project, Supervision's annotators draw labels like
`person 0.87` and `#7 0.87`. They only draw; they don't detect anything.

**Association**: The tracking step that decides which new detection belongs to
which existing track. ByteTrack associates by comparing box overlap (IoU).

**Bounding box**: A rectangle around a detected object, stored as the pixel
coordinates of its top-left and bottom-right corners (`xyxy`).

**Class**: The kind of object a detection is, such as `person`. This project
keeps only the `person` class.

**COCO**: A large public dataset of everyday photos labelled with 80 kinds of
object. The RF-DETR model used here was trained on it, which is why its
classes are general ones like `person`.

**Confidence**: A score from 0 to 1 showing how sure the model is about one
detection.

**Confidence threshold**: The minimum confidence a detection needs to be kept.
The commands default to 0.5; the evaluation compared 0.20, 0.40 and 0.60.

**Detection**: One object the model found in one frame: a bounding box, a
class and a confidence. Also the name of the whole task of finding objects.

**F1**: A single score combining precision and recall. It is high only when
both are high.

**False negative (FN)**: A real person with no box of their own. Includes the
second person under a box that spans two people.

**False positive (FP)**: A box with no real person of its own, such as a bag,
a flag or a duplicate box.

**Fragmentation**: One person's path split across several tracks, usually
after the track was lost and a new one started. Seen in this project after a
fast camera pan.

**Frame**: One still picture from a video. The project's clip has 1091 frames
at about 55 per second.

**Ground truth**: The correct answer that model output is compared against.
Here, the number of real people in each evaluated frame, counted by a
reviewer.

**ID switch**: A tracker ID moving from one person to another. In this
project, `#22` moved from the referee to a player.

**Inference**: Running an already-trained model on new input. Everything
RF-DETR does in this project is inference; nothing is trained.

**IoU (intersection over union)**: How much two boxes overlap, from 0 (not at
all) to 1 (identical). ByteTrack uses it to match boxes to tracks. This
project's evaluation doesn't use it.

**Lost track**: A confirmed track that found no matching detection and is kept
for a short time in case the person reappears.

**mAP (mean average precision)**: The standard detection benchmark metric,
which scores boxes by IoU over many images. This project's evaluation is not
mAP.

**Occlusion**: One object blocking the view of another, such as players in a
maul.

**Precision**: Of the boxes the model drew, the share that were real people:
TP / (TP + FP).

**Pretrained model**: A model already trained by someone else and used as-is.
This project uses pretrained RF-DETR Nano.

**Recall**: Of the real people, the share the model found: TP / (TP + FN).

**Track / tracklet**: The tracker's running record of one object followed over
time. "Tracklet" usually means a short track, often one that ended early.

**tracker_id**: The number a tracker gives a confirmed track, shown as `#7` in
the output. It labels a track, not a player's identity.

**True positive (TP)**: A box on a real person that is that person's only
matched box.

**Unconfirmed track**: In this project, a person detection returned with
`tracker_id == -1`. Usually a new track not yet matched on enough consecutive
frames, or a box ByteTrack didn't assign to any track. Drawn in grey as
`unconfirmed`.
