#!/usr/bin/env python3  # Run with the first python3 found on PATH.

import argparse  # Parse CLI arguments (`seed`, `--out`, `--size`, `--cells`).
import hashlib  # Create a stable hash from the seed string.
import math  # Use sin/cos for radial motif geometry.
from pathlib import Path  # Handle output paths and parent directory creation.

MASK32 = 0xFFFFFFFF  # Keep PRNG state confined to unsigned 32-bit arithmetic.


def make_rng(seed: str):
    # Convert user seed text into deterministic bytes (same text -> same bytes).
    seed_bytes = hashlib.sha256(seed.encode("utf-8")).digest()
    # Use first 4 bytes as initial state; force non-zero to keep xorshift alive.
    state = int.from_bytes(seed_bytes[:4], "big") or 1

    def next_u32() -> int:
        nonlocal state  # Mutate outer `state` on each call.
        state ^= (state << 13) & MASK32  # Xorshift step 1.
        state ^= state >> 17  # Xorshift step 2.
        state ^= (state << 5) & MASK32  # Xorshift step 3.
        state &= MASK32  # Re-apply mask so value stays in 32-bit range.
        return state  # Return one deterministic pseudo-random 32-bit integer.

    return next_u32  # Return function closure so caller can pull random values.


def rand01(next_u32) -> float:
    # Map uint32 output to [0, 1) for probability and scaling math.
    return next_u32() / 4294967296.0


def rgb(next_u32, brighten: bool = True) -> str:
    # Take low byte of next random integer for red channel.
    r = next_u32() & 255
    # Take the next random integer and use bits 8..15 for green channel.
    g = (next_u32() >> 8) & 255
    # Take another random integer and use bits 16..23 for blue channel.
    b = (next_u32() >> 16) & 255
    # Optionally lift dark colors so they show up on dark backgrounds.
    if brighten and (r + g + b) < 180:
        # Compute small per-channel boost needed to clear a minimum brightness.
        bump = (180 - (r + g + b)) // 3 + 1
        # Clamp channel values so they never exceed 255.
        r = min(255, r + bump)
        g = min(255, g + bump)
        b = min(255, b + bump)
    # Return SVG/CSS-compatible color text.
    return f"rgb({r}, {g}, {b})"


def f(x: float) -> str:
    # Format numbers with short precision so SVG stays compact and deterministic.
    return f"{x:.2f}"


def build_svg(seed: str, size: int, cells: int) -> str:
    # Build deterministic RNG function from seed.
    next_u32 = make_rng(seed)
    # Start SVG with required namespace and fixed canvas dimensions.
    parts = [f'<svg xmlns="https://www.w3.org/TR/SVG2/" width="{size}" height="{size}">']
    # Add a full-canvas background rectangle.
    parts.append(f'<rect width="{size}" height="{size}" fill="{rgb(next_u32, brighten=False)}"/>')
    # Compute cell width/height for a square grid.
    cell = size / cells

    # Loop over each row in grid.
    for gy in range(cells):
        # Loop over each column in grid.
        for gx in range(cells):
            # Skip some cells so layout has negative space.
            if rand01(next_u32) < 0.15:
                continue
            # Compute top-left corner of current cell.
            x0 = gx * cell
            # Compute top-left corner Y of current cell.
            y0 = gy * cell
            # Pick shape center with slight jitter inside cell.
            cx = x0 + cell * (0.5 + (rand01(next_u32) - 0.5) * 0.5)
            # Pick shape center Y with similar jitter.
            cy = y0 + cell * (0.5 + (rand01(next_u32) - 0.5) * 0.5)
            # Choose a fill color from PRNG.
            col = rgb(next_u32)
            # Choose shape transparency in a visible range.
            alpha = 0.25 + rand01(next_u32) * 0.65

            # Use PRNG parity to choose between rectangle and circle.
            if next_u32() % 2 == 0:
                # Random rectangle width relative to cell size.
                w = cell * (0.25 + rand01(next_u32) * 0.7)
                # Random rectangle height independent from width.
                h = cell * (0.25 + rand01(next_u32) * 0.7)
                # Emit rectangle element as raw SVG string.
                parts.append(
                    f'<rect x="{f(cx - w / 2)}" y="{f(cy - h / 2)}" width="{f(w)}" height="{f(h)}" '
                    f'fill="{col}" fill-opacity="{f(alpha)}"/>'
                )
            else:
                # Random circle radius relative to cell size.
                r = cell * (0.12 + rand01(next_u32) * 0.35)
                # Emit circle element as raw SVG string.
                parts.append(
                    f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(r)}" '
                    f'fill="{col}" fill-opacity="{f(alpha)}"/>'
                )

    # Compute center point once for signature motif.
    cx, cy = size / 2, size / 2
    # Fixed ray count keeps motif bold and readable.
    rays = 40
    # Inner and outer ray radii as fractions of canvas size.
    inner, outer = size * 0.06, size * 0.32

    # Emit each ray line.
    for i in range(rays):
        # Base evenly spaced angle plus tiny jitter for organic look.
        ang = (2 * math.pi * i / rays) + (rand01(next_u32) - 0.5) * 0.12
        # Per-ray length variation.
        r2 = outer * (0.8 + 0.4 * rand01(next_u32))
        # Start point on inner radius.
        x1, y1 = cx + inner * math.cos(ang), cy + inner * math.sin(ang)
        # End point on varied outer radius.
        x2, y2 = cx + r2 * math.cos(ang), cy + r2 * math.sin(ang)
        # Add one SVG line element for this ray.
        parts.append(
            f'<line x1="{f(x1)}" y1="{f(y1)}" x2="{f(x2)}" y2="{f(y2)}" '
            f'stroke="{rgb(next_u32)}" stroke-width="{f(1 + (next_u32() % 4))}" '
            f'stroke-opacity="0.8" stroke-linecap="round"/>'
        )

    # Add a single center circle to anchor the motif visually.
    parts.append(f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(size * 0.03)}" fill="{rgb(next_u32)}"/>')
    # Close root SVG element.
    parts.append("</svg>")
    # Join with newlines and include one trailing newline for stable file output.
    return "\n".join(parts) + "\n"


def main():
    # Create argument parser for command-line interface.
    parser = argparse.ArgumentParser()
    # Required positional seed string.
    parser.add_argument("seed")
    # Optional output path (default `./out.svg`).
    parser.add_argument("--out", default="./out.svg")
    # Optional square canvas size in pixels.
    parser.add_argument("--size", type=int, default=800)
    # Optional number of grid cells per dimension.
    parser.add_argument("--cells", type=int, default=16)
    # Parse CLI arguments now.
    args = parser.parse_args()

    # Basic input validation so geometry math stays sensible.
    if args.size < 64:
        raise SystemExit("--size must be >= 64")
    # Ensure at least a 2x2 grid.
    if args.cells < 2:
        raise SystemExit("--cells must be >= 2")

    # Build SVG text deterministically from args.
    svg = build_svg(args.seed, args.size, args.cells)
    # Convert output string path to `Path` object.
    out = Path(args.out)
    # Create parent directory if it does not exist.
    out.parent.mkdir(parents=True, exist_ok=True)
    # Write SVG bytes with deterministic newline behavior.
    out.write_text(svg, encoding="utf-8", newline="\n")
    # Print required one-line completion message.
    print(f"Wrote {out} (seed={args.seed})")


if __name__ == "__main__":
    # Run CLI entrypoint only when file is executed directly.
    main()
