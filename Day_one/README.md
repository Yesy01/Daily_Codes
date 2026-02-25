# Hash to Poster (Day One)

Deterministic SVG poster generator in pure Python (standard library only).

## Requirements

- Python 3.9+ (or any recent Python 3)

## Run

From the project folder:

```bash
cd "/root folder"
python3 hash_to_poster.py "hello"
```

That writes `./out.svg` and prints:

```text
Wrote out.svg (seed=hello)
```

## Common Commands

Custom output path:

```bash
python3 hash_to_poster.py "hello" --out samples/hello.svg
```

Custom size and grid density:

```bash
python3 hash_to_poster.py "deadbeef" --size 800 --cells 28 --out samples/deadbeef.svg
```

Wallet-like seed:

```bash
python3 hash_to_poster.py "0x1a2b3c4d5e" --out samples/wallet.svg
```

## Determinism Check

Run twice with the same seed and compare bytes:

```bash
python3 hash_to_poster.py "hello" --out /tmp/a.svg
python3 hash_to_poster.py "hello" --out /tmp/b.svg
cmp -s /tmp/a.svg /tmp/b.svg && echo "same" || echo "different"
```

Expected result: `same`

## Different Seeds Check

```bash
python3 hash_to_poster.py "hello" --out /tmp/hello.svg
python3 hash_to_poster.py "deadbeef" --out /tmp/deadbeef.svg
cmp -s /tmp/hello.svg /tmp/deadbeef.svg && echo "same" || echo "different"
```

Expected result: `different`

## Notes

- Same seed + same flags => same SVG output.
- Different seeds should produce visually different posters.
- Output is plain SVG XML text and can be opened in any browser.
