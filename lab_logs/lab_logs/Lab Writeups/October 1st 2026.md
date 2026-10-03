Lab Results [[Lab Results/October 1st 2026|October 1st 2026]]

Run 1:
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