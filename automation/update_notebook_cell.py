#!/usr/bin/env python3
import json
import sys

cl_cyd = sys.argv[1] if len(sys.argv) > 1 else "/home/pymite6941/Clyde"
nb_path = f"{cl_cyd}/anthropic_student_baseline.ipynb"

with open(nb_path) as f:
    nb = json.load(f)

cell1 = nb['cells'][1]
source = cell1['source']

if isinstance(source, list):
    pass
else:
    source = [line + "\n" for line in source]
    cell1['source'] = source

new_lines = []
i = 0
while i < len(source):
    line = source[i]
    if line.startswith('MODE = '):
        new_lines.append('MODE = "train"           # "smoke" = short Kaggle test | "train" = real session')
    elif line.startswith('TRACK = '):
        trk = sys.argv[2] if len(sys.argv) > 2 else "A"
        new_lines.append(f'TRACK = "{trk}"              # "A" from-scratch tiny GPT   |  "B" LoRA on Qwen 0.5B')
    elif line.startswith('DATA_PACK = '):
        dp = sys.argv[3] if len(sys.argv) > 3 else "english"
        new_lines.append(f'DATA_PACK = "{dp}"    # "english" | "python" | "bugs" | "mixed"')
    elif line.startswith('RUN_NAME = '):
        rn = sys.argv[4] if len(sys.argv) > 4 else "A-english-1"
        new_lines.append(f'RUN_NAME = "{rn}"   # new folder every run')
    elif line.startswith('RESUME_FROM = '):
        rf = sys.argv[5] if len(sys.argv) > 5 else "None"
        new_lines.append(f'RESUME_FROM = {rf}       # e.g. "runs/A-english" ; None = start fresh')
    elif line.startswith('HYPOTHESIS = '):
        if i + 1 < len(source) and 'HYPOTHESIS' in source[i+1]:
            new_lines.append(line)
        else:
            new_lines.append(f'HYPOTHESIS = "Track {trk} on {dp} will train factual assistant."')
    elif line.startswith('SUCCESS_IF = '):
        if i + 1 < len(source) and 'SUCCESS_IF' in source[i+1]:
            new_lines.append(line)
        else:
            new_lines.append(f'SUCCESS_IF = "loss falls across printed steps AND sample contains coherent {dp} content."')
    elif line.startswith('TRACK_A_STEPS = ') or line.startswith('TRACK_B_MAX_STEPS = '):
        new_lines.append(line)
    else:
        new_lines.append(line)
    i += 1

cell1['source'] = new_lines

with open(nb_path, 'w') as f:
    json.dump(nb, f, indent=1)

print("Notebook cell updated successfully")
