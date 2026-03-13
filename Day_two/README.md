# Trait Extractor + Repro Test Harness (Day Two)

Companion verifier for the Day One SVG poster generator.

This tool:

- runs the generator for a list of seeds
- computes a SHA-256 hash for each generated SVG
- extracts simple traits from the raw SVG text
- writes a stable JSON report
- exits with code `1` if repeated runs for the same seed do not match

## Requirements

- Python 3.9+ or another recent Python 3
- no third-party packages

## Project Layout

- [tools/verify_posters.py](/Users/yesie/Documents/Documents%20-%20Yesirat%E2%80%99s%20MacBook%20Air/repos/dailycoding/Day_two/tools/verify_posters.py)
- [seeds.txt](/Users/yesie/Documents/Documents%20-%20Yesirat%E2%80%99s%20MacBook%20Air/repos/dailycoding/Day_two/seeds.txt)
- generator under test: [../Day_one/hash_to_poster.py](/Users/yesie/Documents/Documents%20-%20Yesirat%E2%80%99s%20MacBook%20Air/repos/dailycoding/Day_one/hash_to_poster.py)

## Run

From the repo root:

```bash
python3 Day_two/tools/verify_posters.py \
  --gen ./Day_one/hash_to_poster.py \
  --outdir ./Day_two/samples \
  --seeds ./Day_two/seeds.txt \
  --runs 2 \
  --report ./Day_two/samples/report.json
```

From the `Day_two` folder:

```bash
python3 tools/verify_posters.py \
  --gen ../Day_one/hash_to_poster.py \
  --outdir ./samples \
  --seeds ./seeds.txt \
  --runs 2 \
  --report ./samples/report.json
```

Expected success output:

```text
OK: 3 seeds verified deterministically (runs=2)
```

## What The Report Contains

The report is written as JSON and includes:

- generator path
- run count
- one entry per seed
- repeated hashes for each seed
- determinism result for each seed
- traits extracted from SVG text

Example shape:

```json
{
  "generator": "./Day_one/hash_to_poster.py",
  "runs": 2,
  "seeds": [
    {
      "seed": "hello",
      "hashes": ["...", "..."],
      "deterministic": true,
      "traits": {
        "rects": 111,
        "circles": 111,
        "lines": 40,
        "rgb_occurrences": 262,
        "unique_colors": 262,
        "avg_opacity": 0.563591
      }
    }
  ]
}
```

## Trait Rules

Traits are derived from the SVG text itself:

- `rects`: count of `<rect`
- `circles`: count of `<circle`
- `lines`: count of `<line`
- `rgb_occurrences`: count of `rgb(`
- `unique_colors`: count of distinct `rgb(...)` strings
- `avg_opacity`: average of all `fill-opacity="..."` values, or `null` if none exist

## Files Produced

The verifier writes:

- `samples/seed_0.svg`
- `samples/seed_1.svg`
- `samples/seed_2.svg`
- `samples/report.json`

Each seed always maps to the same output filename pattern: `seed_<index>.svg`.

## Failure Mode

If the same seed produces different hashes across runs, the script prints the failing seeds and exits with code `1`.

Expected failure output shape:

```text
FAIL: determinism mismatch for 1 seed(s)
 - hello
```

## Manual Sabotage Test

To prove the verifier catches non-determinism:

1. Copy the Day One generator.
2. Add a timestamp comment to the generated SVG.
3. Run the verifier against the modified copy.

Example:

```bash
cp Day_one/hash_to_poster.py Day_two/nondet_gen.py
```

Then add:

```python
import time
```

and inside `build_svg(...)` before the return:

```python
parts.append(f"<!-- {time.time_ns()} -->")
```

Run:

```bash
python3 Day_two/tools/verify_posters.py \
  --gen ./Day_two/nondet_gen.py \
  --outdir ./Day_two/samples_nondet \
  --seeds ./Day_two/seeds.txt \
  --runs 2 \
  --report ./Day_two/samples_nondet/report.json
```

Expected result: non-zero exit code and a determinism failure message.
