from __future__ import annotations

from dataclasses import dataclass
import heapq


@dataclass
class FabricSpec:
    w: int
    h: int
    tracks: int = 4
    pins_per_side: int = 4
    switch_box: str = "wilton"
    cb_tracks: str = "all"
    routing_dir: str = "uni"
    track_split: str = "even"
    turn_cost: float = 0.2
    track_dirs: dict[str, int] | None = None
    slices_per_clb: int = 4
    lut_k: int = 4


def place_cells(cells: dict, fabric: FabricSpec) -> dict[str, tuple[int, int]]:
    placements: dict[str, tuple[int, int]] = {}
    x = 0
    y = 0
    for name in sorted(cells.keys()):
        placements[name] = (x, y)
        x += 1
        if x >= fabric.w:
            x = 0
            y += 1
        if y >= fabric.h:
            raise ValueError("Not enough CLBs for placement")
    return placements


def emit_blocks(cells: dict, placements: dict[str, tuple[int, int]]) -> dict:
    blocks: dict[str, dict] = {}
    for name, cell in cells.items():
        x, y = placements[name]
        key = f"x{x}y{y}"
        if cell["type"] == "dff":
            ff = {
                "d": cell["pins"]["d"],
                "q": cell["pins"]["q"],
                "clk": cell["pins"].get("clk", "clk"),
            }
            if "rst" in cell["pins"]:
                ff["rst"] = cell["pins"]["rst"]
            blocks[key] = {"mode": "dff", "inputs": [], "ff": ff}
        elif cell["type"] == "not":
            blocks[key] = {
                "mode": "not",
                "inputs": [cell["pins"]["a"]],
                "ff": None,
            }
        else:
            blocks[key] = {
                "mode": cell["type"],
                "inputs": [cell["pins"]["a"], cell["pins"]["b"]],
                "ff": None,
            }
    return blocks


def route_fnet(module: dict, fabric: FabricSpec, placements: dict[str, tuple[int, int]]) -> dict:
    nets = module["nets"]
    ports = module["ports"]
    cells = module["cells"]
    io_positions = _assign_io_positions(ports, fabric)
    pin_sides = module.get("pin_sides", {}) if isinstance(module, dict) else {}

    net_drivers: dict[str, tuple[str, str]] = {}
    net_sinks: dict[str, list[tuple[str, str]]] = {n: [] for n in nets}

    for pname, pinfo in ports.items():
        if pinfo["dir"] == "in":
            net_drivers[pname] = ("port", pname)
        else:
            net_sinks[pname].append(("port", pname))

    for cname, cell in cells.items():
        for pin, net in cell["pins"].items():
            if _is_output_pin(cell["type"], pin):
                if net in net_drivers:
                    raise ValueError(f"Multiple drivers for net {net}")
                net_drivers[net] = (cname, pin)
            else:
                net_sinks[net].append((cname, pin))

    segments: list[dict] = []
    switches: list[dict] = []
    taps: list[dict] = []

    for net in nets:
        driver = net_drivers.get(net)
        if not driver:
            continue
        for sink in net_sinks.get(net, []):
            segs, sws, tps = _route_point_to_point(
                net, driver, sink, placements, fabric, io_positions, pin_sides, cells
            )
            segments.extend(segs)
            switches.extend(sws)
            taps.extend(tps)

    taps = _dedupe_taps(taps)

    return {
        "nets": _high_level_routes(nets, net_drivers, net_sinks, placements, io_positions, ports),
        "segments": segments,
        "switches": switches,
        "taps": taps,
        "io": _emit_io(ports, io_positions),
    }


def _route_point_to_point(
    net: str,
    src: tuple[str, str],
    dst: tuple[str, str],
    placements: dict[str, tuple[int, int]],
    fabric: FabricSpec,
    io_positions: dict[str, tuple[int, int, str]],
    pin_sides: dict,
    cells: dict,
) -> tuple[list[dict], list[dict], list[dict]]:
    segments: list[dict] = []
    switches: list[dict] = []
    taps: list[dict] = []

    src_block = src[0]
    dst_block = dst[0]
    if src_block == "port":
        x0, y0, _ = io_positions[src[1]]
    else:
        x0, y0 = placements[src_block]
    if dst_block == "port":
        x1, y1, _ = io_positions[dst[1]]
    else:
        x1, y1 = placements[dst_block]

    path = _route_astar((x0, y0), (x1, y1), fabric)
    if path:
        segments.extend(_segments_from_path(net, path, fabric))
        switches.extend(_switches_from_path(net, path, fabric))

    taps.append(
        _tap_for_pin(
            net, src_block, src[1], placements, io_positions, pin_sides, cells, fabric
        )
    )
    taps.append(
        _tap_for_pin(
            net, dst_block, dst[1], placements, io_positions, pin_sides, cells, fabric
        )
    )
    return segments, switches, taps


def _route_astar(
    start: tuple[int, int],
    goal: tuple[int, int],
    fabric: FabricSpec,
) -> list[tuple[int, int]]:
    def heuristic(a: tuple[int, int], b: tuple[int, int]) -> int:
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    start_state = (start[0], start[1], None)
    open_set: list[tuple[float, tuple[int, int, str | None]]] = []
    heapq.heappush(open_set, (0.0, start_state))
    came_from: dict[tuple[int, int, str | None], tuple[int, int, str | None]] = {}
    g_score: dict[tuple[int, int, str | None], float] = {start_state: 0.0}

    while open_set:
        _, current = heapq.heappop(open_set)
        cx, cy, cdir = current
        if (cx, cy) == goal:
            return _reconstruct_path(came_from, current)
        for step_dir, (dx, dy) in (
            ("w", (-1, 0)),
            ("e", (1, 0)),
            ("n", (0, -1)),
            ("s", (0, 1)),
        ):
            if fabric.routing_dir == "uni" and not _direction_allowed(fabric, step_dir):
                continue
            nx, ny = cx + dx, cy + dy
            if nx < 0 or ny < 0 or nx >= fabric.w or ny >= fabric.h:
                continue
            turn_penalty = 0.0 if cdir in (None, step_dir) else fabric.turn_cost
            tentative = g_score[current] + 1.0 + turn_penalty
            next_state = (nx, ny, step_dir)
            if tentative < g_score.get(next_state, 1_000_000.0):
                came_from[next_state] = current
                g_score[next_state] = tentative
                f = tentative + heuristic((nx, ny), goal)
                heapq.heappush(open_set, (f, next_state))
    return []


def _reconstruct_path(
    came_from: dict[tuple[int, int, str | None], tuple[int, int, str | None]],
    current: tuple[int, int, str | None],
) -> list[tuple[int, int]]:
    path = [(current[0], current[1])]
    while current in came_from:
        current = came_from[current]
        path.append((current[0], current[1]))
    path.reverse()
    return path


def _segments_from_path(
    net: str, path: list[tuple[int, int]], fabric: FabricSpec
) -> list[dict]:
    segments: list[dict] = []
    if len(path) < 2:
        return segments
    run_start = path[0]
    run_dir = None
    for i in range(1, len(path)):
        x0, y0 = path[i - 1]
        x1, y1 = path[i]
        step_dir = "h" if y0 == y1 else "v"
        if run_dir is None:
            run_dir = step_dir
            run_start = (x0, y0)
        if step_dir != run_dir:
            flow = _flow_for_run(run_dir, run_start, (x0, y0))
            track = _track_for_flow(net, fabric, flow)
            segments.append(
                _segment_from_run(net, run_dir, run_start, (x0, y0), track, flow)
            )
            run_dir = step_dir
            run_start = (x0, y0)
    flow = _flow_for_run(run_dir, run_start, path[-1])
    track = _track_for_flow(net, fabric, flow)
    segments.append(_segment_from_run(net, run_dir, run_start, path[-1], track, flow))
    return segments


def _segment_from_run(
    net: str,
    run_dir: str,
    start: tuple[int, int],
    end: tuple[int, int],
    track: int,
    flow: str,
) -> dict:
    if run_dir == "h":
        return {
            "net": net,
            "dir": "h",
            "flow": flow,
            "row": start[1],
            "track": track,
            "col0": start[0],
            "col1": end[0],
        }
    return {
        "net": net,
        "dir": "v",
        "flow": flow,
        "col": start[0],
        "track": track,
        "row0": start[1],
        "row1": end[1],
    }


def _switches_from_path(
    net: str, path: list[tuple[int, int]], fabric: FabricSpec
) -> list[dict]:
    switches: list[dict] = []
    for i in range(1, len(path) - 1):
        x0, y0 = path[i - 1]
        x1, y1 = path[i]
        x2, y2 = path[i + 1]
        dir1 = "h" if y0 == y1 else "v"
        dir2 = "h" if y1 == y2 else "v"
        if dir1 != dir2:
            flow1 = _flow_for_step(x0, y0, x1, y1)
            flow2 = _flow_for_step(x1, y1, x2, y2)
            track1 = _track_for_flow(net, fabric, flow1)
            track2 = _track_for_flow(net, fabric, flow2)
            switches.append(
                {
                    "net": net,
                    "sb": f"x{x1}y{y1}",
                    "from": [dir1, track1],
                    "to": [dir2, track2],
                    "from_flow": flow1,
                    "to_flow": flow2,
                }
            )
    return switches


def _tap_for_pin(
    net: str,
    block: str,
    pin: str,
    placements: dict[str, tuple[int, int]],
    io_positions: dict[str, tuple[int, int, str]],
    pin_sides: dict,
    cells: dict,
    fabric: FabricSpec,
) -> dict:
    if block == "port":
        x, y, side = io_positions[pin]
        pin_idx = 0
    else:
        x, y = placements[block]
        cell_type = cells[block]["type"]
        side = _pin_side(pin, pin_sides, cell_type, block)
        pin_idx = _pin_index(cell_type, pin, fabric.pins_per_side)
    flow = _flow_for_side(side)
    track = _track_for_flow(net, fabric, flow)
    return {"net": net, "cb": f"x{x}y{y}", "side": side, "track": track, "pin": pin_idx}


def _is_output_pin(cell_type: str, pin: str) -> bool:
    if cell_type in {"and2", "or2", "xor2", "not"}:
        return pin == "y"
    if cell_type == "dff":
        return pin == "q"
    return False


def _pin_side(pin: str, pin_sides: dict, cell_type: str, cell_name: str | None) -> str:
    cell_map = pin_sides.get(cell_name, {}) if cell_name else {}
    if not cell_map:
        cell_map = pin_sides.get(cell_type, {})
    if pin in cell_map:
        return cell_map[pin]
    if pin in {"a", "b", "d"}:
        return "w"
    if pin in {"y", "q"}:
        return "e"
    if pin in {"clk", "rst"}:
        return "n"
    return "w"


def _pin_index(cell_type: str, pin: str, pins_per_side: int) -> int:
    mapping: dict[str, int] = {}
    if cell_type in {"and2", "or2", "xor2"}:
        mapping = {"a": 0, "b": 1, "y": 0}
    elif cell_type == "not":
        mapping = {"a": 0, "y": 0}
    elif cell_type == "dff":
        mapping = {"d": 0, "q": 0, "clk": 0, "rst": 1}
    idx = mapping.get(pin, 0)
    return max(0, min(pins_per_side - 1, idx))


def build_clb_config(
    module: dict,
    placements: dict[str, tuple[int, int]],
    fabric: FabricSpec,
) -> dict:
    cells = module["cells"]
    pin_sides = module.get("pin_sides", {}) if isinstance(module, dict) else {}
    clb: dict[str, dict] = {}

    for inst, cell in cells.items():
        x, y = placements[inst]
        key = f"x{x}y{y}"
        entry = clb.setdefault(key, {"slices": []})
        slices = entry["slices"]
        slice_idx = len(slices)
        inputs = _slice_inputs(cell, pin_sides, fabric.pins_per_side)
        output = _slice_output(cell, pin_sides, fabric.pins_per_side)
        table = _lut_table(cell["type"], fabric.lut_k)
        slices.append(
            {
                "index": slice_idx,
                "inputs": inputs,
                "table": table,
                "output": output,
            }
        )
    return clb


def _slice_inputs(cell: dict, pin_sides: dict, pins_per_side: int) -> list[str]:
    cell_type = cell["type"]
    inputs: list[str] = []
    for pin in ("a", "b", "d"):
        if pin not in cell["pins"]:
            continue
        side = _pin_side(pin, pin_sides, cell_type, None)
        idx = _pin_index(cell_type, pin, pins_per_side)
        inputs.append(f"{side.upper()}{idx}")
    return inputs


def _slice_output(cell: dict, pin_sides: dict, pins_per_side: int) -> dict:
    cell_type = cell["type"]
    out_pin = "q" if cell_type == "dff" else "y"
    side = _pin_side(out_pin, pin_sides, cell_type, None)
    return {
        "side": side,
        "pin": _pin_index(cell_type, out_pin, pins_per_side),
        "use_ff": cell_type == "dff",
    }


def _lut_table(cell_type: str, lut_k: int) -> list[int]:
    rows = 2 ** max(1, lut_k)
    table: list[int] = []
    for idx in range(rows):
        i0 = (idx >> 0) & 1
        i1 = (idx >> 1) & 1
        if cell_type == "and2":
            out = i0 & i1
        elif cell_type == "or2":
            out = i0 | i1
        elif cell_type == "xor2":
            out = i0 ^ i1
        elif cell_type == "not":
            out = 0 if i0 else 1
        elif cell_type == "dff":
            out = i0
        else:
            out = 0
        table.append(int(out))
    return table


def _assign_io_positions(
    ports: dict, fabric: FabricSpec
) -> dict[str, tuple[int, int, str]]:
    names = sorted(ports.keys())
    io: dict[str, tuple[int, int, str]] = {}
    sides = ["w", "n", "e", "s"]
    for idx, name in enumerate(names):
        side = sides[idx % len(sides)]
        if side == "w":
            io[name] = (0, idx % fabric.h, side)
        elif side == "e":
            io[name] = (fabric.w - 1, idx % fabric.h, side)
        elif side == "n":
            io[name] = (idx % fabric.w, 0, side)
        else:
            io[name] = (idx % fabric.w, fabric.h - 1, side)
    return io


def _emit_io(
    ports: dict, io_positions: dict[str, tuple[int, int, str]]
) -> dict[str, list[dict]]:
    inputs: list[dict] = []
    outputs: list[dict] = []
    for name, info in ports.items():
        x, y, side = io_positions[name]
        entry = {"name": name, "x": x, "y": y, "side": side}
        if info["dir"] == "in":
            inputs.append(entry)
        else:
            outputs.append(entry)
    return {"in": inputs, "out": outputs}


def _dedupe_taps(taps: list[dict]) -> list[dict]:
    seen: set[tuple] = set()
    unique: list[dict] = []
    for tap in taps:
        key = (
            tap.get("net"),
            tap.get("cb"),
            tap.get("side"),
            tap.get("track"),
            tap.get("pin"),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(tap)
    return unique


def _track_for_flow(net: str, fabric: FabricSpec, flow: str) -> int:
    tracks = fabric.tracks
    if tracks <= 1 or fabric.routing_dir != "uni":
        return _track_for_net(net, tracks)
    dirs = _resolved_track_dirs(fabric)
    if flow in {"e", "w"}:
        e_count = max(dirs.get("e", 0), 0)
        w_count = max(dirs.get("w", 0), 0)
        if flow == "e":
            span = max(e_count, 1)
            return _track_for_net(net, span) % span
        base = e_count
        span = max(w_count, 1)
        return base + (_track_for_net(net, span) % span)
    n_count = max(dirs.get("n", 0), 0)
    s_count = max(dirs.get("s", 0), 0)
    if flow == "n":
        span = max(n_count, 1)
        return _track_for_net(net, span) % span
    base = n_count
    span = max(s_count, 1)
    return base + (_track_for_net(net, span) % span)
    return _track_for_net(net, tracks)


def _track_for_net(net: str, tracks: int) -> int:
    if tracks <= 0:
        return 0
    return sum(ord(ch) for ch in net) % tracks


def _resolved_track_dirs(fabric: FabricSpec) -> dict[str, int]:
    if fabric.track_dirs:
        return fabric.track_dirs
    half = fabric.tracks // 2
    extra = fabric.tracks % 2
    return {
        "e": half + extra,
        "w": half,
        "n": half + extra,
        "s": half,
    }


def _direction_allowed(fabric: FabricSpec, flow: str) -> bool:
    dirs = _resolved_track_dirs(fabric)
    return dirs.get(flow, 0) > 0


def _flow_for_step(x0: int, y0: int, x1: int, y1: int) -> str:
    if x1 > x0:
        return "e"
    if x1 < x0:
        return "w"
    if y1 > y0:
        return "s"
    return "n"


def _flow_for_run(run_dir: str, start: tuple[int, int], end: tuple[int, int]) -> str:
    if run_dir == "h":
        return "e" if end[0] >= start[0] else "w"
    return "s" if end[1] >= start[1] else "n"


def _flow_for_side(side: str) -> str:
    if side == "w":
        return "e"
    if side == "e":
        return "w"
    if side == "n":
        return "s"
    return "n"


def _high_level_routes(
    nets: list[str],
    net_drivers: dict[str, tuple[str, str]],
    net_sinks: dict[str, list[tuple[str, str]]],
    placements: dict[str, tuple[int, int]],
    io_positions: dict[str, tuple[int, int, str]],
    ports: dict,
) -> list[dict]:
    routes: list[dict] = []
    for net in nets:
        driver = net_drivers.get(net)
        if not driver:
            continue
        for sink in net_sinks.get(net, []):
            routes.append(
                {
                    "net": net,
                    "path": [
                        _waypoint_for(driver, placements, io_positions, ports),
                        _waypoint_for(sink, placements, io_positions, ports),
                    ],
                }
            )
    return routes


def _waypoint_for(
    endpoint: tuple[str, str],
    placements: dict[str, tuple[int, int]],
    io_positions: dict[str, tuple[int, int, str]],
    ports: dict,
) -> str:
    block, pin = endpoint
    if block == "port":
        direction = ports.get(pin, {}).get("dir", "in")
        return f"{'out' if direction == 'out' else 'in'}:{pin}"
    x, y = placements[block]
    return f"x{x}y{y}.{pin}"
