# FSC Plan (Compiler)

## Goals
- Compile a minimal SHDL (S-expr HDL) subset into a fabric-agnostic netlist plus a fabric-specific bitstream.
- Keep the first iteration small so `fvsim` can simulate and visualize quickly.

## Minimal SHDL Subset (v0)
- Single module per file; no parameterization or generate.
- `ports` and `wire` declarations.
- Explicit primitive instances: `and2`, `or2`, `xor2`, `not`, `dff` (clocked).
- No tri-state, memories, or blocking timing semantics.

## Compilation Pipeline
1. **Parse/Lower**
   - Parse SHDL subset into a simple IR: modules, ports, nets, cells.
   - Normalize expressions to 2-input gates + inverters.
2. **Netlist Emit (Fabric-Agnostic)**
   - Emit a JSON netlist that captures logic graph.
3. **Pack/Place/Route (Fabric-Specific)**
   - Map cells to fabric blocks (LUTs, FFs, IOs).
   - Route nets through fabric channels.
4. **Bitstream Emit**
   - Emit a JSON bitstream that describes block configs + routing.

## Netlist Format (Draft)
File: `*.fnet.json`
```
{
  "top": "top_module",
  "modules": {
    "top_module": {
      "ports": {
        "a": {"dir": "in"},
        "b": {"dir": "in"},
        "y": {"dir": "out"}
      },
      "cells": {
        "u1": {"type": "and2", "pins": {"a": "a", "b": "b", "y": "n1"}},
        "u2": {"type": "not", "pins": {"a": "n1", "y": "y"}}
      },
      "nets": ["a", "b", "n1", "y"]
    }
  }
}
```
Notes:
- Cell `type` is restricted to the minimal primitive set.
- Pins reference net names in `nets`.

## Fabric Assumptions (v0)
- Small grid (e.g., 4x4) of identical logic blocks.
- Each logic block supports 2-input LUT or direct 2-input gate mapping.
- Dedicated FF inside each block for `dff`.
- Simple Manhattan routing with limited channels per edge.

## Bitstream Format (Draft)
File: `*.fbit.json`
```
{
  "fabric": {"w": 4, "h": 4},
  "blocks": {
    "x0y0": {"mode": "and2", "inputs": ["a", "b"], "ff": null},
    "x1y0": {"mode": "not", "inputs": ["n1"], "ff": null}
  },
  "routes": [
    {"net": "a", "path": ["in:a", "x0y0.a"]},
    {"net": "b", "path": ["in:b", "x0y0.b"]},
    {"net": "n1", "path": ["x0y0.y", "x1y0.a"]},
    {"net": "y", "path": ["x1y0.y", "out:y"]}
  ]
}
```
Notes:
- `blocks` records block config (mode, inputs, optional FF).
- `routes` records routing paths as ordered waypoints.

## CLI Sketch
- `fsc compile --in top.shdl --out build/`
  - Emits `build/top.fnet.json` and `build/top.fbit.json`

## Milestones
1. Parser + netlist emit for a 2-input gate subset.
2. Naive placer/router for a fixed grid.
3. Bitstream emit; validate with `fvsim`.
4. Expand expression lowering and add `dff` mapping.
