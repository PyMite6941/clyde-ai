Lab Writeup : [[Lab Writeups/September 29th 2026|September 29th 2026]]

Run 1:
A-config {'n_embd': 128, 'n_head': 4, 'n_layer': 4, 'block': 64, 'vocab': 97}

stream tokens: 13720 | chance-level loss ~ 4.575
fresh weights
step    1  loss=4.5475  1.1s
step   50  loss=2.5848  1.7s
step   80  loss=2.2572  2.0s
saved runs/A-smoke-1/model.pt

=== SAMPLE after A-smoke-1 on pack english ===
The student wroten gro# seafce. ses tppl7en shh-a gdethe . wa.e the Prarorot s lWen one loploPr Ps fthene she s fave grin shorithe. The woD the n the t Ad thetpt toxg se aropa. 
=== end sample ===
Next run: set RESUME_FROM = runs/A-smoke-1 and pick a new DATA_PACK / RUN_NAME

---
Run 2:
A-config {'n_embd': 128, 'n_head': 4, 'n_layer': 4, 'block': 64, 'vocab': 97}

stream tokens: 13720 | chance-level loss ~ 4.575
loaded weights from runs/A-smoke-1/model.pt | previous pack: english
step    1  loss=2.2073  0.0s
step   50  loss=1.6335  0.6s
step   80  loss=1.4711  0.9s
saved runs/A-smoke-1/model.pt

=== SAMPLE after A-smoke-1 on pack english ===
The student wroten grothe s ce.
Enchaparain pha. "te the lo, te thar har on The te ide lldent. Prachedacen te senevene ten chacere. The wrente. nethe thor thote matxt se at pa. 
=== end sample ===
Next run: set RESUME_FROM = runs/A-smoke-1 and pick a new DATA_PACK / RUN_NAME

---
