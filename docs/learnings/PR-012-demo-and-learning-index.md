# PR 012 - Demo Guide and Learning-Note Index

## What I Built

A presentation path through the project, and an index of its development
history. No code changed.

- **`docs/demo.md`**: a 5–10 minute presenter walkthrough. It covers what the
  project does and doesn't do, what to prepare, then four things to show
  (single-frame detection, full-video tracking, evaluation, one failure
  mode), what was learned, questions the project can answer, and links. Each
  step has a rough time and a list of what to point out, not a script.
- **`docs/learnings/README.md`**: an index of the nine learning notes, with
  one sentence per note and short reading paths by topic.
- **`README.md`**: a Demo row in the Documentation table, and the Learning
  notes row now links the index.

## What I Learned

- **Reference docs and a demo answer different questions.** The existing
  docs are organized by topic: how to install, what each command does, what
  detection and tracking are, what goes wrong. A presenter needs an order to
  run things in and a short list of what to point out at each step. None of
  the existing pages gave that without reading several of them.
- **Documentation for learning explains; documentation for demoing
  selects.** The concept guides try to be complete. The demo guide mostly
  leaves things out and links to where they're explained.
- **Choosing what goes into 5–10 minutes.** I kept steps that:
  - run as a single command with a visible result;
  - show one idea each (detect, track, measure, fail);
  - use results the project actually recorded.

  The evaluation step went in partly because `summarize` reads the
  committed review, so it works even if the video or GPU isn't available
  during the demo. Things like the ByteTrack thresholds table and the
  frame-seeking investigation stayed out and are linked instead.
- **Failure modes are worth showing, not hiding.** The most useful thing the
  project demonstrates is that a bad result belongs to a specific layer: a
  grey box is a tracking result, not a missed detection; a new ID after a
  pan is fragmentation, not a new person. Showing one failure explains the
  pipeline better than showing only clean frames.
- **Project observations are clip-specific.** Frame 545, the pan at frames
  825–829 and `#22` exist only on the project's clip. A presenter using
  another video will see different frames, so the demo frames these as "on
  the project's clip" and says what kind of moment to look for instead.
- **An index makes corrections easy to follow.** Several notes are corrected
  by later ones: PR 007 fixed the frame that PR 003 reported, and PR 009
  corrected PR 006's counts. A one-line summary per note, and a reading path
  per topic, make that chain visible without opening every file.

## Important Terms

- **Presenter walkthrough**: a checklist of what to run and what to point
  out, in order, rather than a script.
- **Reading path**: a suggested order for reading related notes on one
  topic.

## Problems I Hit

1. **The repository doesn't record a comparison behind the tool choices.**
   The planned answer to "Why RF-DETR Nano?" could easily have implied Nano
   was chosen over larger sizes. The notes only record that it's the
   smallest pretrained size and that it ran faster than the clip's frame
   rate. Likewise, no other tracker was compared with ByteTrack.
2. **A first draft overstated ByteTrack's benefit.** It said reusing
   lower-confidence detections "helps with partly hidden players", which
   this project didn't measure.
3. **Attributing discoveries to the right PR.** The first draft of the index
   said PR 007 showed the frame 545 problem; PR 006 found it and PR 007
   fixed it. It also said PR 005 traced all 44 IDs to specific causes; the
   note says most.
4. **Describing how corrections are handled.** The first proposal said later
   corrections are added as follow-up sections rather than rewrites. That
   isn't accurate: PR 009 updated PR 006's current figures and also added a
   correction section.
5. **Some PRs have no note.** PRs #1, #2 and #4 were setup and guideline
   changes.

## How I Solved Them

1. The answers say what was recorded (smallest size; 72.7 frames/s against
   the 55.18 fps source in PR 005's run; ByteTrack's low-confidence
   association) and say plainly that no alternatives were compared.
2. Reworded it as a design aim, not a measured result.
3. Checked each index sentence against its note and corrected both.
4. The index now says corrections are documented explicitly while the
   current documentation is kept accurate.
5. The index says those PRs have no learning note, instead of leaving gaps
   unexplained.

### Verification

- Every metric in the demo matched `uv run python -m rugby_vision.evaluation summarize`
  on the committed review.
- Frame, ID and runtime references (545, 825–829, `#22`/`#30`, 44 IDs, at
  most 12 confirmed tracks per frame, 2123 of 11442 unconfirmed, 72.7
  frames/s, about 20 seconds) were checked against the PR 003–008 notes.
- A script resolved every relative link and anchor in the README and docs,
  including all nine learning-note links in the index.
- `markdownlint-cli2` (line-length rule off) reported 0 issues on the
  changed files.
- `pytest`, `ruff check src tests` and `ruff format --check src tests`
  passed.

## What I Would Explain to a Customer

The project now has a short guided demo: run detection on one frame, play
the tracked video, show the evaluation table, and point at one failure. The
failure is part of the demo on purpose, because it shows how the pipeline
works: a grey box means the detector found the person and the tracker
hadn't confirmed them yet, which is a different problem from a missed
person.

There's also an index of the development notes, so anyone reviewing the
project can see what was built, what went wrong and what was corrected, in
order.

## Remaining Questions

- Would the demo still fit in 5–10 minutes on a machine without a GPU,
  where tracking speed hasn't been measured?
- Day 4 will explore the hosted Roboflow workflow. That work hasn't started.
