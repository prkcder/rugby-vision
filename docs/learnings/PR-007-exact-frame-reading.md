# PR 007 - Exact Frame Reading

## What I Built

`read_frame(video_path, frame_index)` in `src/rugby_vision/detection.py`
now returns the exact decoded frame at `frame_index`. It no longer seeks
with `cv2.CAP_PROP_POS_FRAMES`. It decodes forward from the first frame
instead:

```python
for _ in range(frame_index):
    if not capture.grab():
        raise RuntimeError(...)
ok, image = capture.read()
```

Public behavior is unchanged:

- `frame_index=None` still means the middle frame (`frame_count // 2`).
- An out-of-range index still raises `ValueError` before any decoding.
- `Frame.index`, `Frame.fps` and `Frame.frame_count` are reported the same
  way as before.

I also added a unit test where each frame's gray level encodes its index.
It checks that `read_frame()` returns the matching pixels for frames 0, 7,
13 and 19.

## What I Learned

- **Seeking by frame number isn't guaranteed to be frame-accurate for
  compressed video.** On this clip, `CAP_PROP_POS_FRAMES` returned a real
  decoded frame, just not the one requested, and it gave no error.
- **Sequential decoding is correct by construction.** `grab()` decodes a
  frame without converting it to an image. After `frame_index` successful
  grabs, the next `read()` is exactly frame `frame_index`. There's no
  timestamp math.
- **This clip has a variable frame rate.** ffprobe reports
  `r_frame_rate=60/1` but `avg_frame_rate=654600/11863` (about 55.18 fps).
  OpenCV's `CAP_PROP_FPS` gives the 55.18 average.
- **So `Frame.seconds` is only approximate.** `frame.index` now names the
  exact decoded frame. But `frame.index / frame.fps` divides by an average
  rate. For frame 545 it gives 9.88s, while the container timestamp of that
  decoded frame is about 10.08s. OpenCV's `CAP_PROP_POS_MSEC` and ffprobe's
  `pts_time` agree on 10.08s. This PR doesn't change timestamp handling.

## Important Terms

- **Keyframe (I-frame)**: a frame stored as a complete picture.
- **P-/B-frame**: a frame stored as changes from other frames. It can only
  be decoded after the frames it depends on.
- **Random seeking**: jumping to a position in the video without decoding
  everything before it.
- **Sequential decoding**: decoding every frame in order from the start.
- **Variable frame rate (VFR)**: the time between frames isn't constant,
  so frame number × (1 / fps) doesn't match each frame's real timestamp.
- **PTS (presentation timestamp)**: the time the container says a frame
  should be shown.

## Problems I Hit

### Symptom

PR #6 found that `read_frame(video, 545)` returned the wrong image, with no
error. Its pixels were identical to sequentially decoded frame 531.
PR #6 also saw other wrong frames:

- seeking to 80 returned frame 55
- seeking to 831 returned frame 839
- seeking to frame 1075 or later failed outright

So PR 003's "frame 545" result really came from about frame 531.

### Reproduction

1. Open `data/raw/rugby.mp4` with `cv2.VideoCapture`.
2. Call `set(cv2.CAP_PROP_POS_FRAMES, 545)`, then `read()`.
3. Separately, decode frames in order from the start and keep frame 545.
4. Compare the two images with `np.array_equal`.

Result on this machine in this PR:

```text
old seek(545) == sequential 545: False
old seek(545) exact matches:     [531]   (searched sequential frames 500-599)
```

### Root cause (observed behavior vs hypothesis)

**Verified directly:**

- `CAP_PROP_POS_FRAMES` random seeking isn't frame-accurate for this H.264
  source.
- The clip's frame timing is variable.

**Likely explanation (an informed hypothesis, not traced through the
OpenCV or FFmpeg source):**

- H.264 can only start decoding at a keyframe.
- OpenCV's FFmpeg backend likely turns the frame index into a timestamp
  using the stream's frame rate.
- It then seeks to a keyframe near that time and decodes forward to where
  it thinks the target is.
- With a variable frame rate, index × (1 / fps) drifts away from the real
  timestamps, so it lands on a nearby frame.

This fits what we saw: errors in both directions (545→531 early, 831→839
late) and failures near the end of the clip. It isn't proven.

## How I Solved Them

- **The fix:** replaced the seek in `read_frame()` with a `grab()` loop and
  a final `read()`. It's the same sequential approach
  `evaluation.read_frames_sequentially()` already uses. I didn't change
  `evaluation.py` or `tracking.py`.
- **The cost:** every call decodes up to `frame_index` frames. That's fine
  for this short clip, where correctness matters more than speed.
- **A limit of the unit test:** it uses a tiny MJPG video, and every MJPG
  frame is a keyframe, so the old seeking code would likely pass it too.
  It guards "requested index → matching pixels". The regression proof for
  the H.264 clip is the real-clip check below.

### Verification

- **Real clip:** a one-off check compared `read_frame()` with
  `evaluation.read_frames_sequentially()`, a separate decoding loop.

  ```text
  Frame metadata: 545 1091 55.18 9.88s
  read_frame(545) == sequential 545: True
  middle index: 545 True
  0 True
  80 True
  831 True
  1074 True
  1090 True
  ```

  Frames 80 and 831 were wrong under seeking. 1074 and 1090 are near the
  end, where seeking failed. The default (`None`) still resolves to frame
  545.

- **Corrected RF-DETR run:** on the exact frame 545 it gave 11 person
  detections, with confidences 0.90, 0.88, 0.86, 0.86, 0.84, 0.80, 0.75,
  0.73, 0.69, 0.64 and 0.61. The count matches PR 003's historical run on
  about frame 531, but the confidences differ. The PR-003 note records
  both.
- **Automated checks:** `pytest`, `ruff check` and `ruff format --check`
  all pass on `src` and `tests`.

## What I Would Explain to a Customer

When we asked OpenCV to jump straight to frame 545 of this clip, it
quietly gave us a picture from about 14 frames earlier. Compressed video
stores most frames as changes from earlier frames, and this recording's
frame timing isn't perfectly regular, so "jump to frame N" can miss. Now
we decode the video in order up to the requested frame. It's slightly
slower, but the frame we analyse is exactly the one we name. We checked
that against an independent decode of the real clip. Times shown in
seconds are still approximate for this recording.

## Remaining Questions

- Should `Frame.seconds` use the container timestamp
  (`CAP_PROP_POS_MSEC`) instead of `index / fps`, given this clip's
  variable frame rate?
- `evaluation.read_frames_sequentially()` and `read_frame()` now do the
  same kind of decoding in two places. Is it worth sharing one helper?
- Would the hypothesised cause be confirmed by testing seeking on a
  constant-frame-rate re-encode of the same clip?
