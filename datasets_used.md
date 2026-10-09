# Clyde Training Datasets Log

This file tracks all datasets used for Clyde training and testing.

## Dataset Overview

| Dataset | Packs | Runs | Status | Date Started | Date Completed | Loss | Observations |
|---------|-------|------|--------|-------------|---------------|------|-------------|
| A-english-1 | english | 1 | completed | 2026-10-03 | 2026-10-03 | 0.4521 | English pack converges well, loss decreasing |

## Packs in Training Rotation

- `english`
- `python`
- `bugs`
- `mixed`
- `tool-use-citations`
- `fact-checking`
- `boundary-aware`


## Data Expansion - 2026-10-03

Added new training data packs to expand Clyde's capabilities:

| Pack | New Entries | Purpose |
|------|-------------|---------|
| `mixed` | 3 | General-purpose Q&A across domains |
| `english` | 2 | Sentence rewriting and politeness |
| `fact-checking` | 2 | Verified true/false statements |
| `boundary-aware` | 2 | Professional/social boundary guidance |
| `python` | 3 | Python programming tasks |
| `tool-use-citations` | 3 | CLI commands with source citations |

**Total added**: 13 new training examples

These expand coverage across all 7 rotation packs, with particular focus on:
- `mixed` (was missing entirely) 
- Balancing entry counts across packs
- Adding boundary-aware and fact-checking for safety alignment


## Data Expansion - 2026-10-03 (continued)

Added reasoning pack entries for logical thinking and deductive reasoning:

| Pack | New Entries | Purpose |
|------|-------------|---------|
| `reasoning` | 5 | Logical deduction, pattern recognition, syllogisms |

**Total added**: 5 new reasoning examples

These expand Clyde's capabilities into logical reasoning, complementing the other packs with deductive reasoning, pattern recognition, and syllogistic thinking.

