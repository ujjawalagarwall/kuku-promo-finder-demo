# KukuFM — AI Promo Finder (public code-only prototype)

A reproducible, dependency-free Python baseline that identifies and ranks 20–60-second promo candidates in timestamped screenplay episodes. It uses interpretable heuristics; it is **not** a semantic LLM evaluator.

## Requirements

Python 3.9+. No external packages or paid APIs.

## Expected input

Provide a ZIP containing plaintext files named like `episode-001.txt`, `episode-002.txt`, etc. Each file uses the following block format (the example below is entirely fictional):

```text
**NARRATOR:**
Start: (00:00.00) | End: (00:04.00)
A storm is coming.

**CHARACTER A:**
Start: (00:04.00) | End: (00:08.00)
What happened to the map?
```

The script expects minute:second timestamps with decimal fractions and episode filenames containing `episode-<number>`.

## Run

```bash
python3 promo_finder.py "/path/to/input_pack.zip" --output outputs --top 30
```

Run this command from the repository directory. The tool processes ZIP contents in memory, so you do not need to extract the scripts first.

## Generated files

- `outputs/top_promos.csv` — ranked, human-readable shortlist with timestamps, hooks and potential cliffhangers
- `outputs/top_promos.json` — structured shortlist
- `outputs/all_candidates.json` — up to two relatively non-overlapping candidates per episode
- `outputs/run_summary.json` — processing counts and parser diagnostics

## How it works

1. Parse dialogue/action blocks and their timestamps.
2. Generate candidate continuous windows from 20 to 60 seconds.
3. Score opening hooks, potential final-line suspense, conflict language, dialogue density, and context dependence.
4. Remove strongly overlapping candidates per episode and rank globally.

On the assignment's 50-episode input pack, the baseline processed 3,727 timestamped blocks, retained 100 candidates and exported the top 30. The real input and outputs are intentionally **not** published here.

## Limitations

Heuristic question detection is not proof of a strong hook or cliffhanger. Scores are not calibrated engagement predictions, and editors should review context, narrative coherence and feasibility before using segments. A semantic model could be added later to improve these checks; the supplied code does not require one.

## Confidentiality

This public repository contains only algorithm and documentation. The original screenplay pack and its dialogue-containing results are excluded and should be shared only through an arrangement authorized by KukuFM.
