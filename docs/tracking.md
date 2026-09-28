# Tracking

This page explains multi-object tracking: what it adds on top of detection,
how ByteTrack does it in Rugby Vision, and why tracker IDs behave the way
they do on rugby footage.

It builds on [Detection](detection.md). For where tracking sits in the
pipeline and how to run it, see [How it works](how-it-works.md) and
[Commands](commands.md#tracking-full-video). Short definitions are in the
[Glossary](glossary.md).

## Detection vs tracking

> **Detection:** "There is a person here."
>
> **Tracking:** "I think this is the same person I saw in earlier frames."

The detector, RF-DETR, looks at each frame on its own. On two consecutive
frames it might find the same eleven people, but it has no idea they are the
same people. Tracking adds that link across time.

## ByteTrack's role

Rugby Vision uses **ByteTrack**, from Roboflow's `trackers` package. Each
frame, ByteTrack receives the person detections from RF-DETR and decides
which of them continue something it was already following.

ByteTrack never looks at the picture. It only sees the boxes and their
confidence scores. This has two consequences that shape everything below:

- **It can only track what was detected.** If RF-DETR misses someone,
  ByteTrack has nothing to follow.
- **It doesn't know what anyone looks like.** It matches boxes by position
  and movement, not by shirt colour, face or number.

## Tracks and tracker IDs

A **track** is ByteTrack's running record of one object it's following: where
the box is, how fast it's moving, and how long since it was last matched.
A short track, especially one that ends early, is often called a
**tracklet**.

Each confirmed track gets a number, its **`tracker_id`**. In the output
video it's the `#7` in `#7 0.87`. IDs start at 0 and only go up. A new track
never reuses an old number.

### An ID is not a player's identity

`#7` means "the track ByteTrack has been following under the number 7". It
doesn't mean "player 7", or even "the same person for the whole clip". The
same person can end up with several IDs, and one ID can move from one person
to another. The examples below show both happening.

This is why the project's tracking run reported **44 confirmed track IDs**
across the clip. That is not 44 people. Per frame, there were at most 17
person detections, and at most 12 confirmed tracks. The 44 counts every time
ByteTrack started following someone as a new track.

## Association: how detections are matched to tracks

**Association** is the step where the tracker decides which new detection
belongs to which existing track. In plain terms, each frame ByteTrack:

1. **Predicts** where each track's box should be now, based on how it was
   moving. (It uses a Kalman filter, a standard way to estimate position and
   velocity from noisy measurements.)
2. **Compares** each predicted box with each new detection by how much they
   overlap. The overlap measure is **IoU** (intersection over union): 0 means
   no overlap, 1 means identical boxes.
3. **Pairs them up** so each track gets at most one detection and each
   detection at most one track, choosing the pairing with the most overlap
   overall. Pairs that barely overlap are not matched at all.

A matched detection continues the track and inherits its ID. What happens to
the leftovers is where confirmation comes in.

### How ByteTrack uses lower-confidence detections

ByteTrack's distinctive idea is that low-confidence detections are still
useful. A person who is partly hidden often gets a lower score. Throwing that
box away would break their track.

So ByteTrack matches in two rounds:

1. **High-confidence boxes first.** They are matched against all tracks.
2. **Low-confidence boxes second.** They are matched only against tracks that
   are still unmatched after round 1. A low-confidence box can keep an
   existing track alive, but it can't start a new one.

In short: confident boxes can start and continue tracks; less confident boxes
can only continue them.

## Confirmed and unconfirmed detections

ByteTrack doesn't trust a new track straight away. A new track has to be
matched on several consecutive frames before it gets an ID. Until then, and
for some other boxes, ByteTrack returns the detection with the placeholder
**`tracker_id == -1`**.

The project draws these as grey boxes labelled `unconfirmed 0.66` instead
of hiding them. That keeps two different situations visible:

- **No box at all:** RF-DETR didn't detect the person.
- **Grey box:** RF-DETR detected the person, but ByteTrack hasn't given them
  a confirmed track.

`-1` isn't an identity. It means "no confirmed track for this box in this
frame".

### The settings used in this project

The exact rules depend on ByteTrack's settings. Rugby Vision uses the
**defaults of the installed `trackers` 2.6.0 package**, except for the frame
rate (see [Why frame rate matters](#why-frame-rate-matters)). These values
come from that version's source code. Other ByteTrack implementations, or
other versions of this one, may use different defaults.

| Setting in `trackers` 2.6.0 | Default | What it controls |
| --- | --- | --- |
| `high_conf_det_threshold` | 0.6 | Boxes at or above this go into round 1, boxes below it into round 2 |
| `track_activation_threshold` | 0.7 | Minimum confidence for an unmatched box to start a new track |
| `minimum_consecutive_frames` | 2 | Consecutive matches a track needs before it gets an ID |
| `minimum_iou_threshold` | 0.1 | Minimum overlap for a box and a track to be paired |
| `lost_track_buffer` | 30 | How long a lost track is kept, in frames at 30 fps |

With these settings, a person detection comes back as `-1` when:

- it starts a new track (it scored 0.7 or more) that hasn't yet been matched
  on 2 consecutive frames;
- it matched no track and scored between 0.6 and 0.7, too low to start a
  track;
- it scored below 0.6 and matched no track in round 2.

There are two separate thresholds in play. RF-DETR's threshold (0.5 by
default) decides which boxes exist. ByteTrack's thresholds then decide what
each of those boxes is allowed to do. With RF-DETR at 0.5, ByteTrack's
low-confidence round only ever sees boxes scoring from 0.5 to just under 0.6.

### What this looked like in the project

In the full-video run, **2123 of 11442 person detections (about 19%) were
unconfirmed** when drawn.

Many were distant people. On a wide shot around frame 230, several distant
players scored between 0.51 and 0.65: high enough for RF-DETR's 0.5
threshold, but below the 0.7 needed to start a track. They stayed grey.

## When tracks go wrong

### Lost tracks

When a confirmed track finds no matching detection, it isn't deleted
straight away. It becomes a **lost track** and is kept for a short time in
case the person reappears. If a detection matches it again in time, the
track continues with the same ID. If not, the track ends.

In `trackers` 2.6.0, a track that hasn't been confirmed yet gets no such
grace period: it is dropped as soon as it misses a frame.

### Fragmentation

**Fragmentation** is when one person's path is split across several tracks.
The track is lost, the person comes back, and ByteTrack starts a new track
with a new ID.

The clearest example in the project came from a fast camera pan at
frames 825–829, the biggest sustained frame-to-frame change in the clip.
Between frames 824 and 860, nine confirmed IDs ended. Between frames 865 and
900, nine new IDs (28–36) started as players came back into view. Some of
these are probably the same players under new numbers. That wasn't verified
person by person.

Tracks can survive camera motion when detections keep coming. `#22` stayed on
the referee through the pan.

### ID switches

An **ID switch** is when an existing ID moves from one person to another.

The project's clearest case, around frames 850–874:

1. At frame 850, `#22` is the referee and `#23` is a navy-shirted player
   running in front of him.
2. Around frame 862 they overlap. `#23` stops being matched, and `#22`'s box
   stretches to cover both.
3. By frames 870–874, `#22` is on the navy player. The referee reappears
   under a new ID, `#30`.

That one event is both failures at once: an ID switch (`#22` moved to the
player) and fragmentation (the referee lost his track and got `#30`).

The frame-by-frame account is in the
[PR 005 learning note](learnings/PR-005-video-tracking.md).

### Occlusion and dense groups

**Occlusion** means one object blocking the view of another. It hurts
tracking twice:

- The detector may miss the hidden person or give them a low score, so the
  track gets no matching box.
- When boxes overlap heavily, association by overlap becomes ambiguous. Two
  tracks' predicted boxes can both overlap the same detection.

Rugby's mauls and rucks are dense occlusion. At frame 545 the ruck produced
several heavily overlapping tracked boxes. On the wide shot at frame 230, one
tracked box covered two players in a tackle.

## Why frame rate matters

ByteTrack counts time in frames. In `trackers` 2.6.0, `lost_track_buffer=30`
means "30 frames at 30 fps", about one second.

The project's clip runs at about 55.18 fps, not 30. The code passes the real
frame rate to the tracker, which scales the buffer to 56 frames. That's still
about one second of video.

Without that, a lost track would be dropped after 30 frames, only about 0.54
seconds of this clip. People hidden for longer than that, for example in a
maul, would be more likely to come back with a new ID. This project didn't
run the comparison; it follows from how the buffer works.

## Why detection quality limits tracking quality

The tracker can't do better than the detections it receives:

- **Missed detections** leave gaps. A long enough gap ends the track, and the
  person returns with a new ID.
- **Low confidence** can stop a track from ever being confirmed, as with the
  distant people at frame 230.
- **Merged boxes** (one box on two people) leave the second person without a
  track and make ID switches more likely.
- **Duplicate boxes** can start extra tracks.

[Detection](detection.md#why-detection-is-hard-on-rugby-footage) covers why
these detection errors happen on rugby footage.

## These are baseline observations

None of the above shows that ByteTrack is a bad tracker. It shows how one
configuration behaves on one difficult clip:

- Every ByteTrack setting is the library default, apart from the frame rate.
  Nothing was tuned.
- RF-DETR ran at 0.5, so the low-confidence round had few boxes to work with.
- ByteTrack predicts motion from the boxes alone, so a fast camera pan
  (which makes everyone appear to jump sideways) breaks its predictions.
- It uses no appearance information, so it can't recognise a person who
  comes back after being hidden.
- Tracking quality was observed by watching the output, not measured
  against labelled tracks. There are no tracking metrics in this project.

These results are a starting point to compare against, not a verdict.

## Possible future direction

Some trackers compensate for camera motion. They estimate how the whole
picture moved between frames and correct their predictions before matching.
**BoT-SORT** is one example. It may reduce fragmentation after pans like the
one at frames 825–829.

This project doesn't implement or test BoT-SORT or camera-motion
compensation.

## Next

- [Detection](detection.md): where the boxes come from
- [Evaluation](evaluation.md): how detection quality was measured
- [Glossary](glossary.md): short definitions
