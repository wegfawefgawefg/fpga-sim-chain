from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json

from .layout import node_center, track_offsets

DEFAULT_TRACKS = 4


@dataclass
class Route:
    net: str
    path: list[str]


@dataclass
class Segment:
    net: str
    dir: str
    flow: str | None = None
    row: int | None = None
    col: int | None = None
    track: int | None = None
    col0: int | None = None
    col1: int | None = None
    row0: int | None = None
    row1: int | None = None


@dataclass
class Switch:
    net: str
    sb: str
    from_dir: str
    from_track: int
    to_dir: str
    to_track: int
    from_flow: str | None = None
    to_flow: str | None = None


@dataclass
class Tap:
    net: str
    cb: str
    side: str
    track: int
    pin: int


@dataclass
class RoutingData:
    routes: list[Route]
    segments: list[Segment]
    switches: list[Switch]
    taps: list[Tap]
    fabric: dict
    clb: dict
    io: dict


def load_routing(bit_path: Path) -> RoutingData:
    data = json.loads(bit_path.read_text())
    routes_block = data.get("routes", {})
    routes_list: list[Route] = []
    segments_list: list[Segment] = []
    switches_list: list[Switch] = []
    taps_list: list[Tap] = []

    if isinstance(routes_block, list):
        for route in routes_block:
            routes_list.append(Route(net=route.get("net", ""), path=list(route.get("path", []))))
    else:
        for route in routes_block.get("nets", []):
            routes_list.append(Route(net=route.get("net", ""), path=list(route.get("path", []))))
        for seg in routes_block.get("segments", []):
            segments_list.append(
                Segment(
                    net=seg.get("net", ""),
                    dir=seg.get("dir", ""),
                    flow=seg.get("flow"),
                    row=seg.get("row"),
                    col=seg.get("col"),
                    track=seg.get("track"),
                    col0=seg.get("col0"),
                    col1=seg.get("col1"),
                    row0=seg.get("row0"),
                    row1=seg.get("row1"),
                )
            )
        for sw in routes_block.get("switches", []):
            switches_list.append(
                Switch(
                    net=sw.get("net", ""),
                    sb=sw.get("sb", ""),
                    from_dir=sw.get("from", ["", 0])[0],
                    from_track=sw.get("from", ["", 0])[1],
                    to_dir=sw.get("to", ["", 0])[0],
                    to_track=sw.get("to", ["", 0])[1],
                    from_flow=sw.get("from_flow"),
                    to_flow=sw.get("to_flow"),
                )
            )
        for tap in routes_block.get("taps", []):
            taps_list.append(
                Tap(
                    net=tap.get("net", ""),
                    cb=tap.get("cb", ""),
                    side=tap.get("side", ""),
                    track=tap.get("track", 0),
                    pin=tap.get("pin", 0),
                )
            )

    return RoutingData(
        routes=routes_list,
        segments=segments_list,
        switches=switches_list,
        taps=taps_list,
        fabric=data.get("fabric", {}),
        clb=data.get("clb", {}),
        io=data.get("io", {}),
    )


def route_points(
    route: Route,
    origin: tuple[int, int],
    cell: int,
    grid_w: int,
    grid_h: int,
) -> list[tuple[int, int]]:
    points: list[tuple[int, int]] = []
    for idx, waypoint in enumerate(route.path):
        prev_wp = route.path[idx - 1] if idx > 0 else None
        next_wp = route.path[idx + 1] if idx + 1 < len(route.path) else None
        pt = _waypoint_to_point(
            waypoint, route.net, origin, cell, grid_w, grid_h, prev_wp, next_wp
        )
        if pt is not None:
            points.append(pt)
    return points


def segment_points(
    segment: Segment,
    origin: tuple[int, int],
    cell: int,
    fabric: dict,
) -> tuple[tuple[int, int], tuple[int, int]] | None:
    tracks, track_dirs, routing_dir = _track_layout(fabric)
    if segment.dir == "h" and segment.row is not None:
        return (
            _sb_track_point(
                origin,
                cell,
                segment.col0 or 0,
                segment.row,
                segment.track or 0,
                True,
                tracks,
                track_dirs,
                routing_dir,
            ),
            _sb_track_point(
                origin,
                cell,
                segment.col1 or 0,
                segment.row,
                segment.track or 0,
                True,
                tracks,
                track_dirs,
                routing_dir,
            ),
        )
    if segment.dir == "v" and segment.col is not None:
        return (
            _sb_track_point(
                origin,
                cell,
                segment.col,
                segment.row0 or 0,
                segment.track or 0,
                False,
                tracks,
                track_dirs,
                routing_dir,
            ),
            _sb_track_point(
                origin,
                cell,
                segment.col,
                segment.row1 or 0,
                segment.track or 0,
                False,
                tracks,
                track_dirs,
                routing_dir,
            ),
        )
    return None


def switch_point(sb: str, origin: tuple[int, int], cell: int) -> tuple[int, int] | None:
    x, y = _parse_block_coord(sb)
    if x is None or y is None:
        return None
    return node_center(origin, cell, x * 2, y * 2)


def tap_point(
    tap: Tap, origin: tuple[int, int], cell: int, fabric: dict
) -> tuple[int, int] | None:
    x, y = _parse_block_coord(tap.cb)
    if x is None or y is None:
        return None
    row = 2 * y + 1
    col = 2 * x + 1
    tracks, track_dirs, routing_dir = _track_layout(fabric)
    if tap.side in ("n", "s"):
        offsets = track_offsets(cell, tracks, track_dirs, "h", routing_dir)
    else:
        offsets = track_offsets(cell, tracks, track_dirs, "v", routing_dir)
    off = offsets[min(max(tap.track, 0), len(offsets) - 1)]
    if tap.side == "w":
        px, py = node_center(origin, cell, col - 1, row)
        return (px, py + off)
    if tap.side == "e":
        px, py = node_center(origin, cell, col + 1, row)
        return (px, py + off)
    if tap.side == "n":
        px, py = node_center(origin, cell, col, row - 1)
        return (px + off, py)
    if tap.side == "s":
        px, py = node_center(origin, cell, col, row + 1)
        return (px + off, py)
    return None


def _sb_track_point(
    origin: tuple[int, int],
    cell: int,
    sb_col: int,
    sb_row: int,
    track: int,
    horizontal: bool,
    tracks: int,
    track_dirs: dict[str, int] | None,
    routing_dir: str,
) -> tuple[int, int]:
    col = sb_col * 2
    row = sb_row * 2
    cx, cy = node_center(origin, cell, col, row)
    orientation = "h" if horizontal else "v"
    offsets = track_offsets(cell, tracks, track_dirs, orientation, routing_dir)
    off = offsets[min(max(track, 0), len(offsets) - 1)]
    if horizontal:
        return (cx, cy + off)
    return (cx + off, cy)


def _waypoint_to_point(
    waypoint: str,
    net: str,
    origin: tuple[int, int],
    cell: int,
    grid_w: int,
    grid_h: int,
    prev_wp: str | None,
    next_wp: str | None,
) -> tuple[int, int] | None:
    if waypoint.startswith("in:") or waypoint.startswith("out:"):
        neighbor = next_wp or prev_wp
        if neighbor is None:
            return None
        pt = _waypoint_to_point(neighbor, net, origin, cell, grid_w, grid_h, None, None)
        if pt is None:
            return None
        return _nudge_to_edge(pt, waypoint, origin, cell, grid_w, grid_h)
    if "." not in waypoint:
        return None
    block_name, pin = waypoint.split(".", 1)
    x, y = _parse_block_coord(block_name)
    if x is None or y is None:
        return None
    track = _track_index(net)
    row = 2 * y + 1
    col = 2 * x + 1
    if pin in {"a", "b", "d"}:
        return _track_point(origin, cell, col - 1, row, track, vertical=True)
    if pin in {"y", "q"}:
        return _track_point(origin, cell, col + 1, row, track, vertical=True)
    if pin in {"clk", "rst"}:
        return _track_point(origin, cell, col, row - 1, track, vertical=False)
    return _track_point(origin, cell, col, row, track, vertical=True)


def _track_point(
    origin: tuple[int, int],
    cell: int,
    col: int,
    row: int,
    track: int,
    vertical: bool,
) -> tuple[int, int]:
    cx, cy = node_center(origin, cell, col, row)
    offsets = track_offsets(cell)
    offset = offsets[min(max(track, 0), len(offsets) - 1)]
    if vertical:
        return (cx + offset, cy)
    return (cx, cy + offset)


def _track_index(net: str) -> int:
    if not net:
        return 0
    return sum(ord(ch) for ch in net) % max(1, DEFAULT_TRACKS)


def _track_layout(fabric: dict) -> tuple[int, dict[str, int] | None, str]:
    tracks = int(fabric.get("tracks", DEFAULT_TRACKS))
    track_dirs = fabric.get("track_dirs")
    routing_dir = fabric.get("routing_dir", "bi")
    return tracks, track_dirs, routing_dir


def _nudge_to_edge(
    pt: tuple[int, int],
    waypoint: str,
    origin: tuple[int, int],
    cell: int,
    grid_w: int,
    grid_h: int,
) -> tuple[int, int]:
    x, y = pt
    lattice_w = grid_w * 2 + 1
    if waypoint.startswith("in:"):
        return (origin[0] - 14, y)
    if waypoint.startswith("out:"):
        return (origin[0] + lattice_w * cell + 14, y)
    return pt


def _parse_block_coord(name: str) -> tuple[int | None, int | None]:
    if not name.startswith("x") or "y" not in name:
        return None, None
    try:
        x_str, y_str = name[1:].split("y", 1)
        return int(x_str), int(y_str)
    except ValueError:
        return None, None
