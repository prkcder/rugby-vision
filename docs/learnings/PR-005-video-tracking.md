# PR 005 - Full-Video Person Detection and ByteTrack Tracking

## What I Built

`src/rugby_vision/tracking.py` runs the PR 003 detector across the whole
video and adds persistent tracking:

```text
data/raw/rugby.mp4
     ↓  sv.get_video_frames_generator (BGR frames)
     ↓  BGR → RGB
RFDETRNano.predict(threshold=0.5)          model created once
     ↓
filter_people()                            reused from detection.py
     ↓
ByteTrackTracker(frame_rate=55.18).update()  tracker created once
     ↓
TrackAnnotator
  confirmed (tracker_id != -1): per-ID colour, "#7 0.87"
  unconfirmed (tracker_id == -1): grey, "unconfirmed 0.66"
     ↓
sv.VideoSink → outputs/tracked-rugby.mp4
```

Run it with:

```bash
uv run python -m rugby_vision.tracking
```

Unconfirmed detections are drawn instead of dropped, so the video shows the
difference between "RF-DETR missed this person" (no box at all) and "RF-DETR
found this person but ByteTrack has not confirmed a track yet" (grey box).

All ByteTrack parameters are the trackers 2.6.0 defaults except
`frame_rate`, which is set from the video.

Observed run on `data/raw/rugby.mp4`:

```text
Source:       832x384, 55.18 fps, 1091 frames
Device:       cuda
Frames:       1091 written
Time:         15.0s (72.7 frames/s)
Detections:   11442 person, 2123 unconfirmed (tracker_id -1)
Tracker IDs:  44 confirmed: [0 … 43]
Output:       outputs/tracked-rugby.mp4
```

The 15.0 s covers the frame loop only. The whole command took 21.4 s wall
time, including model loading. At 72.7 frames/s, processing ran faster than
the 55.18 fps source, so FP16 was not needed.

The output video read back as 832x384, 55.18 fps, 1091 frames (verified with
`sv.VideoInfo` and by decoding every frame with OpenCV).

## What I Learned

- `ByteTrackTracker.update()` returns **every** detection passed in. Any it
  has not confirmed come back with `tracker_id == -1`. That happens for a
  brand-new box, a track that hasn't yet been matched on 2 consecutive
  frames (`minimum_consecutive_frames=2`), and an unmatched low-confidence
  box. `-1` is not an identity, so it is never shown as one.
- Tracker IDs start at 0 and only increase. 44 IDs does **not** mean 44
  people; it counts how many separate tracks were confirmed.
- The tracker keeps each detection's `confidence` and `data["class_name"]`,
  so labels can still show the RF-DETR score after tracking.
- `frame_rate` matters because `lost_track_buffer=30` is expressed in
  "30 fps frames". At 55.18 fps the tracker scales it to
  `ceil(55.18 / 30 × 30) = 56` frames, still about one second. With the
  default `frame_rate=30`, a lost track would be dropped after 30 frames,
  which is only about 0.54 s of this video.
- RF-DETR's threshold and ByteTrack's thresholds are separate layers.
  RF-DETR at 0.5 decides which boxes exist. ByteTrack's defaults then treat
  those boxes differently: below 0.6 they can only extend existing tracks,
  and only boxes at 0.7 or above can start a new one. On a wide shot around
  frame 230, several distant people scored 0.51–0.65 and stayed grey
  "unconfirmed".
- ByteTrack matches by box overlap and motion only. It has no idea what a
  person looks like, so when two people overlap it can move an ID from one
  to the other.

### What I observed in the tracked video

I sampled output frames (230, 280, 545, 820, 845, 850–880, 900, 1082) and
analysed the per-frame tracker output with a throwaway script (not
committed).

- **Per-frame counts:** person detections per frame had a median of 11 and
  a max of 17. Confirmed tracks per frame had a median of 8 and a max of 12.
  2123 of 11442 person detections (about 19%) were unconfirmed when drawn.
- **ID switch plus track loss (frames ~850–874):**
  - At frame 850, `#22` is the red-shirted referee and `#23` is a navy #9
    player running in front of him at the right edge of the frame.
  - Around frame 862 the two overlap, `#23` stops being matched (last
    matched frame 857), and `#22`'s box stretches to cover both.
  - By frames 870–874, `#22` is on the navy #9 player and the referee has
    a new ID, `#30` (first seen at frame 873).
  - This one event shows two separate failures:
    1. **ID switch:** `#22` moved from the referee onto the navy #9 player.
    2. **Track loss and re-creation:** the referee's original track
       (`#22`) was lost to him, and when the tracker picked him up again
       it created a new track with the new ID `#30`.
- **Fragmentation after a fast camera pan:**
  - Frames 825–829 have the largest sustained frame-to-frame change in the
    clip (mean absolute pixel difference about 18, against a median of 4.3).
    Frames 820 and 845 show the camera swinging to follow play.
  - Between frames 824 and 860, nine confirmed IDs ended (11, 12, 13, 14,
    17, 19, 21, 23, 24).
  - Between frames 865 and 900, nine new IDs (28–36) started as players came
    back into view.
  - A script matching "an ID ended, then a new one started nearby within 60
    frames" flagged pairs such as 19→30, 11→32 and 14→28. Some of these are
    probably the same players with new IDs. I did not verify each identity
    by eye.
- **Stable track through the pan:** `#22` (first confirmed at frame 691)
  was on the referee in sampled frames 820, 845 and 850, so it survived the
  pan until the overlap described above. Tracks can survive camera motion
  when detections keep coming.
- **Dense groups:**
  - In the wide shot at frame 230, one box (`#5`) covers two players in a
    tackle.
  - At frame 545 (the PR 003 frame), the ruck produced several heavily
    overlapping boxes (`#10`, `#15`, `#16`, `#17`, `#9`).
- **End of clip:** frames 1073–1090 have zero detections. The source is a
  phone screen recording, and the last ~18 frames show the phone's
  control-centre overlay, not the match. Short-lived IDs 42 (13 frames) and
  43 (9 frames) appear just before it.

## Important Terms

- **Tracklet / track**: the tracker's running record for one object: Kalman
  filter state (position and velocity of the box), frames since last match,
  count of consecutive matches, and ID.
- **`tracker_id`**: the tracker's label meaning "the same thing I've been
  following". It is not a player identity. `-1` means not confirmed.
- **Confirmed track**: a track matched on `minimum_consecutive_frames`
  (default 2) consecutive frames. Only confirmed tracks get an ID.
- **Lost track buffer**: how long an unmatched track is kept alive waiting
  to be matched again.
- **ID switch**: an existing ID moves to a different person (`#22`
  referee → player).
- **Fragmentation**: one person's track is lost and they come back under a
  new ID (the referee re-created as `#30` after losing `#22`; the post-pan
  IDs 28–36).
- **Two-stage association**: ByteTrack matches high-confidence boxes
  (≥ 0.6) first, then tries low-confidence boxes against the tracks still
  unmatched.

## Problems I Hit

1. **Many more IDs than people.** The run produced 44 confirmed IDs, while
   PR 003's manual review estimated roughly 13 people visible in one frame.
2. **Unconfirmed detections needed their own style.** Supervision's
   `ColorLookup.TRACK` colours boxes by `tracker_id`, so a `-1` box would
   still get a palette colour and look like a real track.
3. **Output FPS is rounded.** The source reports 55.17997 fps and the
   written MP4 reports 55.18 fps. The frame count and resolution match
   exactly.

## How I Solved Them

1. Investigated instead of tuning. Per-ID lifespans, sampled frames and a
   frame-difference check traced most of the extra IDs to a fast camera pan
   (frames 825–829), one overlap-driven ID switch (`#22`), and players
   leaving and re-entering view. Parameter tuning and trackers with camera
   motion compensation were out of scope for this PR.
2. Drew the two groups with separate annotators: confirmed tracks use
   per-ID colours, and unconfirmed detections use a single grey with the
   label `unconfirmed <confidence>`.
3. Accepted as-is. The difference is below a thousandth of a frame per
   second and comes from how the MP4 stores the frame rate.

## What I Would Explain to a Customer

We ran the person detector on every frame of the clip and linked the
detections over time so each player gets a number. It processes about 73
frames per second on the GPU, faster than the clip plays.

The numbers are only as stable as what the camera can see. When the camera
pans quickly or two people overlap, the tracker can lose someone and give
them a new number, or pass a number from one person to another. We saw both
in this clip, including a referee's number moving to a player.

The tracker assigned 44 numbers in total. That counts tracks, not people.

## Remaining Questions

- How much would BoT-SORT's camera motion compensation reduce the
  fragmentation after the pan at frames 825–829?
- Would a lower RF-DETR threshold (so ByteTrack's low-confidence stage gets
  more boxes), or a lower `track_activation_threshold`, confirm the distant
  players that stayed grey without adding false tracks?
- How should the phone screen-recording overlay at the end of the clip be
  handled: trim the source, or detect and skip those frames?
