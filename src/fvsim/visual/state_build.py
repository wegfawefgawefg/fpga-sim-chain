from __future__ import annotations

import random

from .routes import RoutingData
from .state import (
    CBCell,
    CBTap,
    CLBCell,
    FabricState,
    IOPad,
    SBCell,
    SBConnection,
    Slice,
    SliceOutput,
)


def build_state_from_routing(
    routing: RoutingData,
    grid_w: int,
    grid_h: int,
    demo: bool = False,
    cdemo: bool = False,
    seed: int = 0xD00D,
) -> FabricState:
    fabric = dict(routing.fabric or {})
    fabric.setdefault("w", grid_w)
    fabric.setdefault("h", grid_h)
    fabric.setdefault("tracks", 4)
    fabric.setdefault("pins_per_side", 4)
    fabric.setdefault("slices_per_clb", 4)
    fabric.setdefault("lut_k", 4)
    fabric.setdefault("routing_dir", "bi")
    fabric.setdefault("track_dirs", None)
    fabric.setdefault("switch_box", "wilton")

    if demo or cdemo:
        return build_demo_state(fabric, seed=seed, colored=cdemo)

    sb = _sb_from_routing(routing)
    cb = _cb_from_routing(routing)
    clb = _clb_from_routing(routing, fabric, seed=seed)
    io = _io_from_routing(routing)
    return FabricState(fabric=fabric, sb=sb, cb=cb, clb=clb, io=io)


def build_demo_state(
    fabric: dict,
    seed: int = 0xD00D,
    colored: bool = False,
) -> FabricState:
    rng = random.Random(seed)
    sb: dict[tuple[int, int], SBCell] = {}
    cb: dict[tuple[int, int, str], CBCell] = {}
    w = int(fabric.get("w", 1))
    h = int(fabric.get("h", 1))

    for x in range(w + 1):
        for y in range(h + 1):
            base = _demo_sb_connections(x * 2, y * 2)
            connections: list[SBConnection] = []
            for idx, (sa, ia, sb_side, ib) in enumerate(base):
                net = f"sb{x}_{y}_{idx}_{rng.randint(0, 9999)}" if colored else None
                connections.append(SBConnection(sa, ia, sb_side, ib, net))
            sb[(x, y)] = SBCell(x=x, y=y, connections=connections)

    for x in range(w):
        for y in range(h):
            for side in ("w", "e", "n", "s"):
                taps: list[CBTap] = []
                for idx, (s, t, p) in enumerate(_demo_cb_taps(x, y, side)):
                    net = f"cb{x}_{y}_{side}_{idx}_{rng.randint(0, 9999)}" if colored else None
                    taps.append(CBTap(s, t, p, net))
                cb[(x, y, side)] = CBCell(x=x, y=y, side=side, taps=taps)

    clb = _demo_clb_state(fabric, rng)
    io = _demo_io_state(fabric, rng, cb, colored=colored)
    return FabricState(fabric=fabric, sb=sb, cb=cb, clb=clb, io=io)


def _sb_from_routing(routing: RoutingData) -> dict[tuple[int, int], SBCell]:
    sb: dict[tuple[int, int], SBCell] = {}
    for sw in routing.switches:
        x, y = _parse_block_coord(sw.sb)
        if x is None or y is None:
            continue
        side_in = _flow_to_side_in(sw.from_flow, sw.from_dir)
        side_out = _flow_to_side_out(sw.to_flow, sw.to_dir)
        if side_in is None or side_out is None:
            continue
        conn = SBConnection(side_in, sw.from_track, side_out, sw.to_track, sw.net)
        key = (x, y)
        cell = sb.get(key)
        if cell is None:
            sb[key] = SBCell(x=x, y=y, connections=[conn])
        else:
            cell.connections.append(conn)
    return sb


def _cb_from_routing(routing: RoutingData) -> dict[tuple[int, int, str], CBCell]:
    cb: dict[tuple[int, int, str], CBCell] = {}
    for tap in routing.taps:
        x, y = _parse_block_coord(tap.cb)
        if x is None or y is None:
            continue
        key = (x, y, tap.side)
        entry = cb.get(key)
        tap_entry = CBTap(tap.side, tap.track, tap.pin, tap.net)
        if entry is None:
            cb[key] = CBCell(x=x, y=y, side=tap.side, taps=[tap_entry])
        else:
            entry.taps.append(tap_entry)
    return cb


def _clb_from_routing(
    routing: RoutingData, fabric: dict, seed: int
) -> dict[tuple[int, int], CLBCell]:
    if not routing.clb:
        rng = random.Random(seed ^ 0xC0DE)
        return _demo_clb_state(fabric, rng)
    clb: dict[tuple[int, int], CLBCell] = {}
    for name, entry in routing.clb.items():
        x, y = _parse_block_coord(name)
        if x is None or y is None:
            continue
        slices: list[Slice] = []
        for raw in entry.get("slices", []):
            idx = int(raw.get("index", 0))
            inputs = list(raw.get("inputs", []))
            table = list(raw.get("table", []))
            out = raw.get("output", {})
            output = SliceOutput(
                side=str(out.get("side", "e")),
                pin=int(out.get("pin", 0)),
                use_ff=bool(out.get("use_ff", False)),
            )
            slices.append(Slice(index=idx, inputs=inputs, table=table, output=output))
        clb[(x, y)] = CLBCell(x=x, y=y, slices=slices)
    return clb


def _io_from_routing(routing: RoutingData) -> list[IOPad]:
    io: list[IOPad] = []
    if not routing.io:
        return io
    for entry in routing.io.get("in", []):
        io.append(_io_from_entry(entry, "in"))
    for entry in routing.io.get("out", []):
        io.append(_io_from_entry(entry, "out"))
    return io


def _io_from_entry(entry: dict, kind: str) -> IOPad:
    return IOPad(
        name=str(entry.get("name", "")),
        x=int(entry.get("x", 0)),
        y=int(entry.get("y", 0)),
        side=str(entry.get("side", "w")),
        kind=kind,
        pin=int(entry.get("pin")) if entry.get("pin") is not None else None,
        track=int(entry.get("track")) if entry.get("track") is not None else None,
        net=str(entry.get("net")) if entry.get("net") is not None else None,
    )


def _demo_clb_state(fabric: dict, rng: random.Random) -> dict[tuple[int, int], CLBCell]:
    clb: dict[tuple[int, int], CLBCell] = {}
    w = int(fabric.get("w", 1))
    h = int(fabric.get("h", 1))
    pins = int(fabric.get("pins_per_side", 4))
    slices_per = int(fabric.get("slices_per_clb", 4))
    lut_k = int(fabric.get("lut_k", 4))
    lut_inputs = max(1, lut_k)
    sources = (
        [f"W{i}" for i in range(pins)]
        + [f"E{i}" for i in range(pins)]
        + [f"N{i}" for i in range(pins)]
        + [f"S{i}" for i in range(pins)]
    )
    out_sides = ["e", "s", "w", "n"]
    rows = 2 ** lut_inputs
    for x in range(w):
        for y in range(h):
            slices: list[Slice] = []
            for sidx in range(slices_per):
                inputs = [rng.choice(sources) for _ in range(lut_inputs)]
                table = [rng.randint(0, 1) for _ in range(rows)]
                out_side = rng.choice(out_sides)
                out_pin = rng.randint(0, max(0, pins - 1))
                output = SliceOutput(out_side, out_pin, bool(rng.randint(0, 1)))
                slices.append(Slice(index=sidx, inputs=inputs, table=table, output=output))
            clb[(x, y)] = CLBCell(x=x, y=y, slices=slices)
    return clb


def _demo_io_state(
    fabric: dict,
    rng: random.Random,
    cb: dict[tuple[int, int, str], CBCell],
    colored: bool,
) -> list[IOPad]:
    w = int(fabric.get("w", 1))
    h = int(fabric.get("h", 1))
    tracks = int(fabric.get("tracks", 4))
    pins_per_side = int(fabric.get("pins_per_side", 4))
    pads: list[IOPad] = []
    if w <= 0 or h <= 0:
        return pads
    used_names = [f"p{idx}" for idx in range(20)]
    slots: list[tuple[str, int, int, int]] = []
    for y in range(h):
        for pin in range(pins_per_side):
            slots.append(("w", 0, y, pin))
            slots.append(("e", w - 1, y, pin))
    for x in range(w):
        for pin in range(pins_per_side):
            slots.append(("n", x, 0, pin))
            slots.append(("s", x, h - 1, pin))
    rng.shuffle(slots)
    used_map: dict[tuple[str, int, int, int], str] = {}
    for idx, name in enumerate(used_names):
        if idx >= len(slots):
            break
        used_map[slots[idx]] = name
    used_order = list(used_map.values())

    for side, x, y, pin in slots:
        name = used_map.get((side, x, y, pin))
        is_used = name is not None
        if not name:
            name = f"{side}{x}y{y}p{pin}"
        kind = "in" if is_used and (used_order.index(name) < len(used_order) // 2) else "out"
        net = None
        if is_used and colored:
            net = f"io_{name}_{rng.randint(0, 9999)}"
        elif is_used:
            net = name
        track = min(pin, max(0, tracks - 1))
        pad = IOPad(
            name=name,
            x=x,
            y=y,
            side=side,
            kind=kind,
            pin=pin,
            track=track,
            net=net if is_used else None,
        )
        pads.append(pad)
        if is_used:
            cb_key = _cb_key_for_pad(pad)
            if cb_key:
                cb_x, cb_y, cb_side = cb_key
                tap = CBTap(cb_side, track, pin, net)
                key = (cb_x, cb_y, cb_side)
                cell = cb.setdefault(key, CBCell(cb_x, cb_y, cb_side, []))
                cell.taps.append(tap)
    return pads


def _cb_key_for_pad(pad: IOPad) -> tuple[int, int, str] | None:
    x = pad.x
    y = pad.y
    side = pad.side
    if side == "w":
        return (x, y, "w")
    if side == "e":
        return (x, y, "e")
    if side == "n":
        return (x, y, "n")
    if side == "s":
        return (x, y, "s")
    return None


def _parse_block_coord(name: str) -> tuple[int | None, int | None]:
    if not name.startswith("x") or "y" not in name:
        return None, None
    try:
        x_str, y_str = name[1:].split("y", 1)
        return int(x_str), int(y_str)
    except ValueError:
        return None, None


def _flow_to_side_in(flow: str | None, direction: str) -> str | None:
    if direction == "h":
        return "w" if flow == "e" else "e" if flow == "w" else None
    if direction == "v":
        return "n" if flow == "s" else "s" if flow == "n" else None
    return None


def _flow_to_side_out(flow: str | None, direction: str) -> str | None:
    if direction == "h":
        return "e" if flow == "e" else "w" if flow == "w" else None
    if direction == "v":
        return "s" if flow == "s" else "n" if flow == "n" else None
    return None


def _demo_sb_connections(col: int, row: int) -> list[tuple[str, int, str, int]]:
    key = (col + row) % 6
    if key == 0:
        return [("n", 0, "e", 1), ("w", 2, "s", 3), ("n", 1, "s", 1)]
    if key == 1:
        return [("n", 2, "s", 2), ("w", 0, "e", 0)]
    if key == 2:
        return [("n", 3, "e", 3), ("n", 3, "s", 3)]
    if key == 3:
        return [("w", 1, "e", 2), ("w", 1, "n", 1)]
    if key == 4:
        return [("s", 0, "e", 0), ("s", 0, "w", 0), ("n", 1, "w", 1)]
    return [("n", 2, "w", 1), ("s", 1, "e", 2)]


def _demo_cb_taps(col: int, row: int, side: str) -> list[tuple[str, int, int]]:
    if (col + row) % 3 == 0:
        return [(side, 0, 0), (side, 2, 1)]
    if (col + row) % 3 == 1:
        return [(side, 1, 2)]
    return [(side, 3, 3)]
