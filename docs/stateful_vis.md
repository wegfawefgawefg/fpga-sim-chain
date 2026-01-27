# Stateful Visualizer Plan

This document proposes a state-driven rendering model for `fvsim` that removes direct
bitstream-to-render coupling. The goal is to configure a persistent per-cell state
from a bitstream (or demo generator) and then render *only* from that state. This
prevents alignment issues and preserves the existing visual capabilities.

## Goals

- **State-first rendering**: rendering reads only from cell state, not directly from fbit.
- **No regressions**: keep all current visual features (CLB internals, CB/SB coloring,
  IO pads, lane labels, arrows, demo/cdemo, zoom/pan toggles).
- **Deterministic**: state is fully defined by the input (bitstream or demo seed).
- **Fabric-aware**: track offsets, directions, and lane labels derive from fabric spec.

## Non-goals (for this phase)

- Full simulator-driven activity (real net values) — still future work.
- Timing-accurate propagation or congestion.
- Replacing the router or bitstream emitter now.

## Key Idea

Introduce an explicit **State Model** that mirrors the visual infrastructure:

- `SBCell` (switch box)
- `CBCell` (connection box)
- `CLBCell` (logic block)

A new **state builder** ingests either:

- `fbit` (real) -> produces cell states
- demo/cdemo generator -> produces cell states

Rendering becomes pure: `render(state, fabric_spec)`. No `fbit` or demo logic inside
render paths.

## Proposed Data Model

### FabricSpec

Pulled from `fbit.fabric`:
- `w`, `h`, `tracks`, `pins_per_side`
- `routing_dir`, `track_dirs`
- `switch_box` (wilton)

### SBCell

- `coords`: (x, y)
- `connections`: list of enabled internal links
  - Each entry: `{ side_a, track_a, side_b, track_b, net_id }`
- `net_colors`: optional mapping if using per-net colors (demo/cdemo)

### CBCell

- `coords`: (x, y)
- `side`: `w|e|n|s` (which CB relative to CLB)
- `taps`: list of enabled tap points
  - Each entry: `{ side, track, pin, net_id }`

### CLBCell

- `coords`: (x, y)
- `slices`: list of `SliceState`

`SliceState`:
- `inputs`: list of input sources (e.g. `W0`, `N1`)
- `lut_table`: bitlist of size `2^lut_k`
- `output`: `{ side, pin, use_ff }`
- `ff_value`: stored FF value (for display; initially 0)

## State Builder

### 1) Real bitstream -> state

Inputs:
- `fbit.routes.taps` -> CB tap state
- `fbit.routes.switches` -> SB connections
- `fbit.clb` -> CLB slice configs
- `fbit.io` -> IO pad state

Output:
- `FabricState` struct with per-cell SB/CB/CLB state arrays

### 2) Demo / cdemo -> state

- Reuse existing demo wiring logic but emit **state objects** instead of drawing.
- `--demo`: monochrome state
- `--cdemo`: per-net colored state

### State model container

`FabricState`:
- `fabric`: FabricSpec
- `sb`: dict[(x,y)] -> SBCell
- `cb`: dict[(x,y,side)] -> CBCell
- `clb`: dict[(x,y)] -> CLBCell
- `io`: list of IO pad entries

## Rendering Pipeline

1) Compute layout metrics (cell size, offsets).
2) Render background grid + lane labels.
3) Render **CB/SB/CLB** from `FabricState`.
   - CB: draw CB box, internal tracks, then highlight only `taps`.
   - SB: draw SB box, internal tracks, then highlight only `connections`.
   - CLB: draw CLB box, slice internals, and I/O labels.
4) Draw IO pads and stubs.

No direct reading of `fbit.routes` inside renderer.

## Directionality & Tracks

- Lane offsets are derived from `fabric.track_dirs` (or even split fallback).
- SB/CB render functions accept **pre-resolved offsets** from the `FabricState`.
- `net_id` is opaque; renderer uses a stable color map keyed by `net_id`.

## Compatibility / No Regression Checklist

- Zoom/pan, lane labels, CB/SB/CLB labels remain.
- `--demo` output matches current demo look.
- `--cdemo` output uses random net colors.
- CLB internals (LUT, FF, tables, input labels) remain.
- IO pads remain.

## Implementation Steps (planned)

1) **Define state dataclasses** in `src/fvsim/visual/state.py`.
2) **Build state from fbit** in `src/fvsim/visual/state_build.py`.
3) **Build demo/cdemo state** using existing demo logic.
4) **Refactor draw paths** to accept `FabricState` instead of `fbit`.
5) **Wire `run_visual`** to call state builder based on `--demo/--cdemo/--bit`.
6) **Remove any direct fbit usage** from rendering functions.

## Open Questions

- IO pads live in FabricState (decision).
- One net per CB tap; fanout means one net drives multiple taps, not multiple nets on one tap.

## Expected Outcome

After this refactor, rendering is stable and purely driven by explicit state
objects. Demo and real bitstreams behave identically with respect to the
infrastructure, and any misalignment becomes a **state-building** bug, not a
rendering bug.
