# FPGA Sim Chain: Pipeline Spec (v0)

This document defines the intermediary artifacts that connect `fsc` and `fvsim`.
It focuses on being minimal, deterministic, and educational.

## Artifacts
- `*.fnet.json`: fabric-agnostic netlist from Verilog.
- `*.fbit.json`: fabric-specific placement + routing + block config.

## Conventions
- Names are ASCII and case-sensitive.
- Net names are unique within a module.
- Ports are nets that also appear in `ports`.
- Values use `0`, `1`, or `X` (unknown). `X` should propagate.
- Clock name defaults to `clk` if not specified on a `dff`.
- Optional reset pin name is `rst` when present; reset value is `0` unless specified.

## Netlist Format (`*.fnet.json`)
### Shape
```
{
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
  "fabric": {"w": 4, "h": 4},
  "blocks": {
    "x0y0": {"mode": "and2", "inputs": ["a", "b"], "ff": null}
  },
  "routes": [
    {"net": "a", "path": ["in:a", "x0y0.a"]}
  ]
}
```

### Block Naming
- `x{col}y{row}` with origin at top-left.
- `mode`: one of primitive types above.
- `inputs`: list of net names in pin order (`a`, `b` or `a`).
- `ff`: `null` or an object for `dff` use:
  - `{ "d": "net", "q": "net", "clk": "clk", "rst": "rst" }`

### Routing Paths
- A route is a list of waypoints from source to sink.
- Waypoints are simple string tokens:
  - `in:<port>` for top-level inputs
  - `out:<port>` for top-level outputs
  - `xNyM.<pin>` for block pins, where `<pin>` is `a`, `b`, or `y`
- `fvsim` resolves point-to-point connectivity by concatenating these paths.

## Simulation Expectations
- Combinational logic evaluated in topological order each tick.
- `dff` updates on rising clock edge (tick boundaries in `fvsim`).
- `X` propagates through gates unless fully determined (e.g., `0 & X -> 0`).
- If a net has multiple drivers, that is an error in v0.

## Validation Strategy
- Golden examples include:
  - Verilog source
  - `*.fnet.json`
  - `*.fbit.json`
  - Expected per-tick net values

