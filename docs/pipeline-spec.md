# FPGA Sim Chain: Pipeline Spec (v0)

This document defines the intermediary artifacts that connect `fsc` and `fvsim`.
It focuses on being minimal, deterministic, and educational.

## Artifacts
- `*.shdl`: S-expr HDL source.
- `*.fnet.json`: fabric-agnostic netlist from SHDL.
- `*.fbit.json`: fabric-specific placement + routing + block config.

## Conventions
- Names are ASCII and case-sensitive.
- Net names are unique within a module.
- Ports are nets that also appear in `ports`.
- Values use `0`, `1`, or `X` (unknown). `X` should propagate.
- Clock name defaults to `clk` if not specified on a `dff`.
- Optional reset pin name is `rst` when present; reset value is `0` unless specified.

## SHDL Source Format (`*.shdl`)
### Shape
```
(module top
  (ports (in a) (in b) (out y))
  (wire n1)
  (and2 u1 a b n1)
  (not u2 n1 y))
```

### Grammar (EBNF)
```
file        = module ;
module      = "(" "module" symbol { form } ")" ;
form        = ports | wire | cell ;
ports       = "(" "ports" { port } ")" ;
port        = "(" ( "in" | "out" ) symbol ")" ;
wire        = "(" "wire" symbol { symbol } ")" ;
cell        = gate2 | not1 | dff ;
gate2       = "(" ( "and2" | "or2" | "xor2" ) symbol symbol symbol symbol ")" ;
not1        = "(" "not" symbol symbol symbol ")" ;
dff         = "(" "dff" symbol { dff_pin } ")" ;
dff_pin     = "(" ( "d" | "q" | "clk" | "rst" ) symbol ")" ;
symbol      = /[^()\\s;]+/ ;
```

### Rules (v0)
- One module per file; `module` name must be unique in the file.
- `ports` entries are `(in <name>)` or `(out <name>)`.
- `wire` declares internal nets.
- Primitive instances are S-exprs:
  - `(and2 <inst> <a> <b> <y>)`
  - `(or2 <inst> <a> <b> <y>)`
  - `(xor2 <inst> <a> <b> <y>)`
  - `(not <inst> <a> <y>)`
  - `(dff <inst> (d <net>) (q <net>) (clk <net>) (rst <net>)?)`
- `clk` and `rst` are optional in `dff`. Default clock net is `clk` if omitted.

## Netlist Format (`*.fnet.json`)
### Shape
```
{
  "fabric": {
    "w": 4,
    "h": 4,
    "tracks": 4,
    "pins_per_side": 4,
    "switch_box": "wilton",
    "cb_tracks": "all",
    "routing_dir": "uni",
    "turn_cost": 0.2,
    "track_dirs": {"e": 2, "w": 2, "n": 2, "s": 2},
    "slices_per_clb": 4,
    "lut_k": 4
  },
  "top": "module_name",
  "modules": {
    "module_name": {
      "ports": {
        "a": {"dir": "in"},
        "y": {"dir": "out"}
      },
      "cells": {
        "u1": {"type": "and2", "pins": {"a": "a", "b": "b", "y": "n1"}}
      },
      "nets": ["a", "b", "n1", "y"]
    }
  }
}
```

### Primitive Types (v0)
- `and2`, `or2`, `xor2`, `not`
- `dff` (rising-edge)

### Cell Pin Conventions
- `and2`, `or2`, `xor2`: `a`, `b`, `y`
- `not`: `a`, `y`
- `dff`: `d`, `q`, optional `clk`, optional `rst`
  - If `clk` pin omitted, it is `clk` by default.
  - If `rst` pin omitted, no reset is used.

## Bitstream Format (`*.fbit.json`)
### Shape
```
{
  "fabric": {
    "w": 4,
    "h": 4,
    "tracks": 4,
    "pins_per_side": 4,
    "switch_box": "wilton",
    "cb_tracks": "all"
  },
  "blocks": {
    "x0y0": {"mode": "and2", "inputs": ["a", "b"], "ff": null}
  },
  "routes": {
    "nets": [
      {"net": "a", "path": ["in:a", "x0y0.a"]}
    ],
    "segments": [
      {"net": "a", "dir": "h", "row": 1, "track": 0, "col0": 0, "col1": 3},
      {"net": "a", "dir": "v", "col": 2, "track": 1, "row0": 0, "row1": 2}
    ],
    "switches": [
      {"net": "a", "sb": "x2y1", "from": ["h", 0], "to": ["v", 1]}
    ],
    "taps": [
      {"net": "a", "cb": "x2y1", "side": "w", "track": 0}
    ]
  }
  "io": {
    "in": [{"name": "a", "x": 0, "y": 0, "side": "w"}],
    "out": [{"name": "y", "x": 3, "y": 0, "side": "e"}]
  }
}
```

### Block Naming
- `x{col}y{row}` with origin at top-left.
- `mode`: one of primitive types above.
- `inputs`: list of net names in pin order (`a`, `b` or `a`).
- `ff`: `null` or an object for `dff` use:
  - `{ "d": "net", "q": "net", "clk": "clk", "rst": "rst" }`

### Fabric Spec
- `w`, `h`: grid size in CLB tiles.
- `tracks`: number of routing tracks per channel.
- `switch_box`: topology, e.g. `wilton`.
- `cb_tracks`: which tracks are connectable to CLB pins (`all` for v0).
- `pins_per_side`: number of CLB pins per side (I/O stubs for connection boxes).
- `slices_per_clb`: number of LUT/FF slices per CLB (default 4).
- `lut_k`: LUT input count per slice (e.g., 4 or 6).
- `routing_dir`: routing directionality (`uni` or `bi`).
- `turn_cost`: extra routing cost for directional turns (router heuristic).
- `track_dirs`: optional per-direction track counts per channel. For horizontal channels,
  `e` + `w` must equal `tracks`. For vertical channels, `n` + `s` must equal `tracks`.
  Example:
  - `"track_dirs": {"e": 2, "w": 2, "n": 2, "s": 2}`

### Fabric Spec File
`fsc bit` can load a standalone fabric spec JSON file. Keys mirror the `fabric` block
in the `*.fbit.json` output. Missing keys fall back to CLI defaults.

Example: `docs/fabric/default.fabric.json`.
- `pin_sides`: optional per-cell pin side mapping. Example:
  - `"pin_sides": {"and2": {"a":"w", "b":"n", "y":"e"}, "dff": {"d":"w", "q":"e", "clk":"s"}}`

### Routing (Two Levels)
`routes.nets` (high-level):
- A route is a list of waypoints from source to sink.
- Waypoints are simple string tokens:
  - `in:<port>` for top-level inputs
  - `out:<port>` for top-level outputs
  - `xNyM.<pin>` for block pins
- Valid `<pin>` values:
  - `a`, `b`, `y` for combinational inputs/outputs
  - `d`, `q`, `clk`, `rst` for `dff` pins

`routes.segments` (low-level, fabric-aware):
- Horizontal segments: `{ "dir": "h", "row": <sb_row>, "track": <t>, "col0": <c0>, "col1": <c1>, "flow": "e"|"w" }`
- Vertical segments: `{ "dir": "v", "col": <sb_col>, "track": <t>, "row0": <r0>, "row1": <r1>, "flow": "n"|"s" }`

`routes.switches` (switch-box turns):
- `{ "sb": "xNyM", "from": ["h"|"v", <t>], "to": ["h"|"v", <t>], "from_flow": "n"|"s"|"e"|"w", "to_flow": "n"|"s"|"e"|"w" }`

`routes.taps` (connection-box taps):
- `{ "cb": "xNyM", "side": "n"|"s"|"e"|"w", "track": <t>, "pin": <p> }`

### IO Placement (v0)
- `io.in` / `io.out` list IO port locations on the fabric edge.
- Each entry: `{ "name": <port>, "x": <col>, "y": <row>, "side": "n"|"s"|"e"|"w" }`.

### Router Notes (v0)
- Initial router is Manhattan-only (A* on the CLB grid) with a fixed track per flow direction.
- For `routing_dir=uni`, A* only expands moves that have available track capacity in `track_dirs`.
- CB taps are emitted at both source and sink pins for visibility.
- Switches are emitted at L-bends only.
- Ports are placed on all four sides in round-robin order.
- Routing segments can be `uni` or `bi` via `routing_dir`. For `uni`, direction is encoded in `flow`.

## Simulation Expectations
- Combinational logic evaluated in topological order each tick.
- `dff` updates on rising clock edge (tick boundaries in `fvsim`).
- `X` propagates through gates unless fully determined (e.g., `0 & X -> 0`).
- If a net has multiple drivers, that is an error in v0.

## Validation Strategy
- Golden examples include:
  - SHDL source
  - `*.fnet.json`
  - `*.fbit.json`
  - Expected per-tick net values
