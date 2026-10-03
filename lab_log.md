# Clyde lab log

One block per Kaggle session. Fill **before** Run all, then finish **after** the sample prints.

If a row is blank, that session does not count as you developing Clyde. It counts as the notebook running.

---

## Experiment 1 — Session 0 smoke (Track A / english)

- Date:
- Kaggle notebook name: `clyde-smoke`
- MODE: `smoke`
- TRACK: `A`
- DATA_PACK: `english`
- RUN_NAME: `A-smoke-1`
- RESUME_FROM: `None`
- Hypothesis: Track A on english will drop loss below chance and the sample will contain common English words.
- Success if: loss falls across printed steps AND sample is not random symbols.

### After the run

- `cuda: True`?  yes / no
- GPU name:
- step 1 loss:
- last step loss:
- Did loss fall?  yes / no
- Sample (paste 3–6 lines):
- Saved `runs/A-smoke-1/` via Save Version?  yes / no
- Verdict: pass / fail
- Next change (only one): e.g. resume Track A on `python`, still smoke

---

## Experiment 2

- Date:
- MODE:
- TRACK:
- DATA_PACK:
- RUN_NAME:
- RESUME_FROM:
- Hypothesis:
- Success if:

### After the run

- `cuda: True`?
- step 1 loss:
- last step loss:
- Sample notes:
- Eval.jsonl tried? (never train on it):
- Verdict:
- Next change (only one):

---

## Experiment 3

- Date:
- MODE:
- TRACK:
- DATA_PACK:
- RUN_NAME:
- RESUME_FROM:
- Hypothesis:
- Success if:

### After the run

- Verdict:
- Next change (only one):

---

## Backlog (ideas, not this session)

- Add 10 real bugs from my own files to `training_data/sft.jsonl`
- Track B smoke after Track A smoke passes
- Score `eval.jsonl` by hand
- Mix pack if English dies after a Python-only run
