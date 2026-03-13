#!/usr/bin/env python3  # Run this file with Python 3 from the current environment.

from __future__ import annotations  # Store type hints as deferred strings.

import argparse  # Parse command-line flags like --gen and --report.
import hashlib  # Compute SHA-256 hashes for generated SVG files.
import json  # Write the final report in JSON format.
import os  # Check whether the generator path is executable.
import re  # Extract traits from raw SVG text using regex.
import subprocess  # Run the external poster generator.
import sys  # Reuse the current Python interpreter for .py generator files.
from pathlib import Path  # Work with filesystem paths safely and clearly.

FILL_OPACITY_RE = re.compile(r'fill-opacity="([0-9]*\.?[0-9]+)"')  # Match numeric fill-opacity values.
RGB_RE = re.compile(r"rgb\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*\)")  # Match rgb(...) color strings.


def parse_args() -> argparse.Namespace:  # Define the CLI and return parsed arguments.
    parser = argparse.ArgumentParser(  # Create the main argument parser.
        description="Verify SVG determinism for a list of seeds."  # Describe the tool in --help output.
    )
    parser.add_argument(  # Add the required generator path argument.
        "--gen", required=True, help="Path to generator script or executable"  # Accept a .py file or executable.
    )
    parser.add_argument(  # Add the required output directory argument.
        "--outdir", required=True, help="Directory where generated SVG files are written"  # Store seed_<index>.svg here.
    )
    parser.add_argument(  # Add the required seeds file argument.
        "--seeds", required=True, help="Text file with one seed per line"  # Blank lines will be ignored.
    )
    parser.add_argument(  # Add the optional run count argument.
        "--runs", type=int, default=2, help="How many runs to perform for each seed"  # Default to two runs.
    )
    parser.add_argument(  # Add the required report file argument.
        "--report", required=True, help="Path to write the JSON report"  # Save the stable report here.
    )
    return parser.parse_args()  # Parse the CLI input and return it to the caller.


def read_seeds(path: Path) -> list[str]:  # Load and clean the list of seeds from disk.
    seeds = [  # Build a list of non-empty, trimmed seed strings.
        line.strip()  # Remove surrounding whitespace from each line.
        for line in path.read_text(encoding="utf-8").splitlines()  # Read the file as UTF-8 text.
        if line.strip()  # Keep only lines that still contain text after trimming.
    ]
    if not seeds:  # Fail early if the file did not contain any usable seeds.
        raise SystemExit(f"No seeds found in {path}")  # Stop with a clear message.
    return seeds  # Hand the cleaned seed list back to the caller.


def build_gen_cmd(gen_path: Path, seed: str, out_svg: Path) -> list[str]:  # Build the subprocess command.
    if gen_path.suffix == ".py" or not os.access(gen_path, os.X_OK):  # Use Python for .py files or non-executables.
        return [sys.executable, str(gen_path), seed, "--out", str(out_svg)]  # Call the script with this interpreter.
    return [str(gen_path), seed, "--out", str(out_svg)]  # Call executable generators directly.


def run_generator(gen_path: Path, seed: str, out_svg: Path) -> None:  # Run the generator once for one seed.
    cmd = build_gen_cmd(gen_path, seed, out_svg)  # Prepare the exact command to execute.
    proc = subprocess.run(cmd, capture_output=True, text=True)  # Execute it and collect stdout/stderr as text.
    if proc.returncode != 0:  # Handle generator failures with a useful error message.
        msg = [  # Start collecting lines for the failure report.
            f"Generator failed for seed={seed!r}",  # Show which seed triggered the failure.
            f"Command: {' '.join(cmd)}",  # Show the exact command that was attempted.
        ]
        if proc.stdout.strip():  # Include stdout only when it contains something useful.
            msg.append(f"stdout:\n{proc.stdout.strip()}")  # Add captured stdout to the message.
        if proc.stderr.strip():  # Include stderr only when it contains something useful.
            msg.append(f"stderr:\n{proc.stderr.strip()}")  # Add captured stderr to the message.
        raise SystemExit("\n".join(msg))  # Abort the program with the collected diagnostics.


def sha256_file(path: Path) -> str:  # Return the SHA-256 digest of a file as a hex string.
    return hashlib.sha256(path.read_bytes()).hexdigest()  # Hash the raw file bytes exactly as written.


def extract_traits(svg_text: str) -> dict[str, object]:  # Compute a small stable trait summary from SVG text.
    opacities = [float(value) for value in FILL_OPACITY_RE.findall(svg_text)]  # Parse all fill-opacity numbers.
    avg_opacity = round(sum(opacities) / len(opacities), 6) if opacities else None  # Average them or use null.
    rgb_matches = RGB_RE.findall(svg_text)  # Collect every rgb(...) occurrence that appears in the SVG.
    return {  # Return a JSON-friendly trait dictionary.
        "rects": svg_text.count("<rect"),  # Count rectangle tags.
        "circles": svg_text.count("<circle"),  # Count circle tags.
        "lines": svg_text.count("<line"),  # Count line tags.
        "rgb_occurrences": svg_text.count("rgb("),  # Count all rgb( occurrences as a simple color proxy.
        "unique_colors": len(set(rgb_matches)),  # Count distinct rgb(...) values.
        "avg_opacity": avg_opacity,  # Include the average fill opacity or null.
    }


def main() -> int:  # Orchestrate argument parsing, generation, hashing, and reporting.
    args = parse_args()  # Read CLI arguments first.
    gen_path = Path(args.gen)  # Convert the generator path string into a Path object.
    if not gen_path.exists():  # Fail early if the generator path is wrong.
        raise SystemExit(f"Generator not found: {gen_path}")  # Stop with a clear path error.
    if args.runs < 1:  # Reject invalid run counts.
        raise SystemExit("--runs must be >= 1")  # Tell the user the minimum valid value.

    seeds_path = Path(args.seeds)  # Convert the seeds path string into a Path object.
    if not seeds_path.exists():  # Fail early if the seeds file is missing.
        raise SystemExit(f"Seeds file not found: {seeds_path}")  # Stop with a clear path error.
    seeds = read_seeds(seeds_path)  # Load the cleaned list of seeds.

    outdir = Path(args.outdir)  # Convert the output directory string into a Path object.
    outdir.mkdir(parents=True, exist_ok=True)  # Create the output directory if it does not exist yet.

    report_rows: list[dict[str, object]] = []  # Accumulate one report entry per seed.
    failed_seeds: list[str] = []  # Track any seeds that produce mismatched hashes.

    for idx, seed in enumerate(seeds):  # Process seeds in a stable order with an index for file naming.
        out_svg = outdir / f"seed_{idx}.svg"  # Reuse the same stable output filename for this seed.
        hashes: list[str] = []  # Store the hash from each run for this seed.
        first_svg_text = ""  # Keep the first SVG text so traits come from the actual generated output.

        for run_idx in range(args.runs):  # Regenerate the same seed multiple times.
            run_generator(gen_path, seed, out_svg)  # Ask the generator to write the SVG file.
            svg_text = out_svg.read_text(encoding="utf-8")  # Read back the generated SVG as text.
            if run_idx == 0:  # Save the first run for trait extraction.
                first_svg_text = svg_text  # Keep the first SVG text unchanged.
            hashes.append(sha256_file(out_svg))  # Hash the file bytes from this run.

        deterministic = len(set(hashes)) == 1  # The seed is deterministic only if every hash matches.
        if args.runs >= 2 and not deterministic:  # Record failures only when determinism was actually tested.
            failed_seeds.append(seed)  # Save the seed value for the final failure summary.

        report_rows.append(  # Add this seed's full result to the report list.
            {
                "seed": seed,  # Keep the original seed string in the report.
                "hashes": hashes,  # Include every run hash for debugging and proof.
                "deterministic": deterministic,  # State whether the repeated runs matched.
                "traits": extract_traits(first_svg_text),  # Compute traits from the first generated SVG.
            }
        )

    report = {  # Build the final top-level JSON report object.
        "generator": args.gen,  # Store the generator path exactly as the user passed it.
        "runs": args.runs,  # Store how many runs were requested.
        "seeds": report_rows,  # Store the per-seed verification results.
    }

    report_path = Path(args.report)  # Convert the report path string into a Path object.
    report_path.parent.mkdir(parents=True, exist_ok=True)  # Create the report directory if needed.
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")  # Write stable pretty JSON.

    if failed_seeds:  # Exit with failure if any seed broke determinism.
        print(f"FAIL: determinism mismatch for {len(failed_seeds)} seed(s)")  # Print a summary line first.
        for seed in failed_seeds:  # Print each failing seed on its own line.
            print(f" - {seed}")  # Make the failing seed easy to spot.
        return 1  # Return a non-zero status code for CI or shell scripts.

    print(f"OK: {len(seeds)} seeds verified deterministically (runs={args.runs})")  # Print the success summary.
    return 0  # Return zero so the shell knows verification succeeded.


if __name__ == "__main__":  # Run the CLI only when this file is executed directly.
    raise SystemExit(main())  # Exit the process with the status code returned by main().
