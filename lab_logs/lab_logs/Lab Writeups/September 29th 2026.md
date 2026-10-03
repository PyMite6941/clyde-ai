Lab Results : [[Lab Results/September 29th 2026|September 29th 2026]]

Run 1:
env: kaggle
torch: 2.10.0+cu128 | cuda: True
gpu: Tesla T4
this run saves to: /kaggle/working/runs/A-smoke-1
resume from: None
SMOKE vs TRAIN: smoke
This is a wiring test. Loss should move a little. Do not judge Clyde from a smoke run.

TRACK != B, skip SFT

--
This was a very basic first test, nothing useful output. Just gibberish, now testing from resume and hopefully something good shows up.

---
Run 2:
PLAN
  mode:       smoke
  track:      A
  pack:       english
  run:        A-smoke-1
  resume:     runs/A-smoke-1
  a_steps:    80
  b_steps:    10
  hypothesis: Track A on english will drop loss below chance and the sample will contain common English words.
  success if: loss falls across printed steps AND sample is not random symbols.
env: kaggle
torch: 2.10.0+cu128 | cuda: True
gpu: Tesla T4
this run saves to: /kaggle/working/runs/A-smoke-1
resume from: runs/A-smoke-1
SMOKE vs TRAIN: smoke
This is a wiring test. Loss should move a little. Do not judge Clyde from a smoke run.

TRACK != B, skip SFT

--
The results this time are better, at least this time there is no # in the response. Seems to be approaching English soon, maybe in a few more tests