# Visual Demo (Fbit)

This bitstream is hand-crafted to exercise the visual routing grid.
It uses a 4x4 fabric and defines four routes that cover:
- Horizontal across the top row
- Vertical down the left-center column
- An L-shaped turn
- A horizontal run on the clock channel

Run:

```bash
PYTHONPATH=src .venv/bin/python -m fvsim visual --bit docs/examples/visual-demo/top.fbit.json --grid 4x4
```
