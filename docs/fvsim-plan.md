# FVSIM Plan (Simulator + Visualizer)

## Goals
- The visual fabric view is a primary feature (pygame): see blocks and routes light up as nets toggle.
- Load `*.fnet.json` and `*.fbit.json` produced by `fsc`.
- Simulate logic with a simple clocked model.

## Inputs
- Netlist (`*.fnet.json`): logical graph + ports.
- Bitstream (`*.fbit.json`): placement + routing + block config.
- Optional stimulus file (future): pin toggles over time.

## Simulation Model (v0)
- **Combinational**: evaluate gates in topological order per cycle.
- **Sequential**: `dff` updates on rising clock edge.
- **Clock**: fixed period in sim config.
- **IO**: inputs driven by a simple script or CLI overrides.

## Core Data Structures
- Fabric grid of blocks: `Block[x][y]` with `mode`, `inputs`, `ff_state`.
- Net graph: resolved from routing paths into point-to-point connections.
- Signal table: `net_name -> value` (0/1/X).

## Execution Flow
1. **Load** netlist and bitstream.
2. **Build** routed connectivity graph from `routes`.
3. **Place** netlist cells into blocks using `blocks` config.
4. **Simulate**:
   - Apply inputs for tick `t`.
   - Evaluate combinational logic.
   - Latch sequential outputs on clock edge.
   - Update net values.
5. **Render** block states and toggles.

## Visualization (pygame)
- Grid of blocks with color indicating output value:
  - 0: dark, 1: bright, X: gray.
- Optional overlay showing last toggle time or activity heatmap.
- Left panel for IO pin values and clock tick count.
 - Static fabric view first (grid + block labels), then animate nets.

## CLI Sketch
- `fvsim run --net build/top.fnet.json --bit build/top.fbit.json`
- `fvsim run --net ... --bit ... --ticks 100 --clock 10ms`
- `fvsim visual --bit build/top.fbit.json`

## Milestones
1. Load netlist/bitstream and build connectivity graph.
2. Simulate combinational gates (no clock).
3. Add `dff` and clocked behavior.
4. Add pygame visualization and basic IO controls.
