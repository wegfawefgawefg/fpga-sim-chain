# Bitstream → Visualizer State Plan

Goal: ensure FBIT fully configures SB/CB/CLB state for a specific fabric, so the visualizer can be driven **only** by state derived from the bitstream.

## Scope

- Update **bitstream schema** so it contains all information needed to set SB/CB/CLB/IO state.
- Keep SHDL/FNET clean (logic only). Fabric‑specific decisions live in router + bitstream.
- Visualizer remains state‑driven (no direct FBIT → draw logic).

## Definitions

- **Fabric spec**: physical architecture (grid size, tracks, pins, switch topology, LUT/FF layout).
- **Bitstream**: fully specified configuration for that fabric.
- **State**: per‑cell SB/CB/CLB/IO settings derived from the bitstream.

## What’s Missing Today (and Needs To Be Represented)

1) **Explicit CLB slice mapping**
   - Slice index per cell, LUT inputs, LUT table, output side/pin, use_ff.
   - Without this, LUT row highlighting and output wiring is ambiguous.

2) **IO → fabric entry**
   - IO pad position is currently just a label; we need to record **which CB tap(s) it drives/receives**.
   - Otherwise inputs appear “inside” the fabric with no entry wiring.

3) **Pin side + pin index determinism**
   - Must be either:
     - Derived from fabric spec + cell type, or
     - Serialized explicitly in bitstream.
   - The router cannot reliably map netlist pins to CB pins without it.

4) **Complete SB/CB activation**
   - Every active net must be represented by:
     - SB connections: side/track ↔ side/track
     - CB taps: side/track ↔ pin index
   - No implicit connections; the bitstream should list all enabled switches/taps.

5) **Fabric‑aware legality**
   - Router must validate against:
     - track_dirs / routing_dir
     - tracks per direction
     - pins per side
     - switch box topology (wilton only for now)
     - slices_per_clb / lut_k

## Proposed Bitstream Additions

### 1) `fabric` block (required)

Must include:
- `w`, `h`
- `tracks`
- `routing_dir` (bi/uni)
- `track_dirs` (if uni)
- `pins_per_side`
- `switch_box` (wilton)
- `slices_per_clb`
- `lut_k`

### 2) `clb` block (required)

Each CLB contains explicit slice configs:

```
clb: {
  "x0y0": {
    "slices": [
      { "index": 0,
        "inputs": ["W0","N1","E0","S0"],
        "table": [0,1,1,0, ...],
        "output": { "side":"e", "pin":0, "use_ff": true }
      },
      ...
    ]
  }
}
```

### 3) `routes` block (required)

All physical routing must be explicit:

```
routes: {
  "taps": [
    { "net":"n1", "cb":"x0y0", "side":"w", "track":1, "pin":0 }
  ],
  "switches": [
    { "net":"n1", "sb":"x0y0", "from":["h",1], "to":["v",2],
      "from_flow":"e", "to_flow":"s" }
  ]
}
```

### 4) `io` block (required)

IO pad position + **explicit connection into fabric**:

```
io: {
  "in":  [{ "name":"a", "x":0, "y":0, "side":"w", "tap": { ... } }],
  "out": [{ "name":"y", "x":1, "y":1, "side":"e", "tap": { ... } }]
}
```

The `tap` can reference a CB side/track/pin so IO entry is unambiguous.

## Pipeline Responsibilities

### SHDL → FNET
- Pure logic graph (cells, nets, ports).
- No fabric assumptions.

### Router
- Takes: FNET + Fabric spec.
- Produces:
  - Placement (cell → CLB coord + slice index).
  - Routing (segments/switches/taps).
  - CLB slice configs (inputs/table/output/use_ff).
  - IO → CB tap mapping.

### Bitstream emitter
- Serializes:
  - Fabric spec
  - CLB slice configs
  - All switches/taps
  - IO pad + tap mapping

### Visualizer
- Loads bitstream → builds state
- Renders only from state

## Validation Plan

1) **Tiny fabric (2x2)** with one net.
2) Expected taps/switches drawn via CB/SB infrastructure.
3) LUT row highlight matches input bit pattern.
4) IO pad shows a clear entry/exit into CB.

## Non‑Goals (for this phase)

- Timing analysis, congestion modeling
- Multiple switchbox topologies
- Multi‑length routing segments

## Next Steps

1) Update fabric spec schema (if needed).
2) Router emits full CLB + IO + routes.
3) Bitstream writer serializes all required fields.
4) Visualizer state builder verifies all fields exist and errors if missing.
