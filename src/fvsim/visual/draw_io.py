from __future__ import annotations

from .layout import cb_size, clb_size, lattice_dims, node_center, track_offsets
from .draw_util import _net_color, _pin_offsets_for_side


def draw_io_pads(
    surface,
    origin: tuple[int, int],
    cell: int,
    grid_w: int,
    grid_h: int,
    io,
    font,
    fabric: dict | None = None,
    cb_state: dict | None = None,
) -> None:
    import pygame

    if not io:
        return
    pads = _normalize_pads(io)
    pad_color = (90, 96, 106)
    in_color = (120, 160, 210)
    out_color = (180, 140, 120)
    unused_color = (110, 110, 120)
    lattice_w, lattice_h = lattice_dims(grid_w, grid_h)
    fabric_w = lattice_w * cell
    fabric_h = lattice_h * cell
    x0, y0 = origin
    edge_color = (90, 96, 106)
    cb_half = cb_size(cell) // 2
    cell_half = cell // 2
    tracks = int((fabric or {}).get("tracks", 4)) if fabric else 4
    pins_per_side = int((fabric or {}).get("pins_per_side", 4)) if fabric else 4
    track_dirs = (fabric or {}).get("track_dirs") if fabric else None
    routing_dir = (fabric or {}).get("routing_dir", "bi") if fabric else "bi"

    for entry, kind in pads:
        if hasattr(entry, "x"):
            x = int(entry.x)
            y = int(entry.y)
            side = entry.side
            name = entry.name
            pin = entry.pin
            track = entry.track
            net = entry.net
        else:
            x = int(entry.get("x", 0))
            y = int(entry.get("y", 0))
            side = entry.get("side", "w")
            name = entry.get("name", "")
            pin = entry.get("pin")
            track = entry.get("track")
            net = entry.get("net")
        if track is None and cb_state is not None:
            track = _infer_pad_track(cb_state, x, y, side, net)
        if pin is None and cb_state is not None:
            pin = _infer_pad_pin(cb_state, x, y, side, net)
        col = 2 * x + 1
        row = 2 * y + 1
        cx, cy = node_center(origin, cell, col, row)
        offset = cell // 2 + 8
        edge_pt = None
        if side in ("w", "e"):
            offsets = track_offsets(cell, tracks, track_dirs, "v", routing_dir)
            off = offsets[_clamp_idx(track, offsets)]
            edge_x = x0 if side == "w" else x0 + fabric_w
            edge_pt = (edge_x, cy + off)
        else:
            offsets = track_offsets(cell, tracks, track_dirs, "h", routing_dir)
            off = offsets[_clamp_idx(track, offsets)]
            edge_y = y0 if side == "n" else y0 + fabric_h
            edge_pt = (cx + off, edge_y)
        if side in ("w", "e"):
            px = edge_pt[0] + (-offset if side == "w" else offset)
            py = edge_pt[1]
        else:
            px = edge_pt[0]
            py = edge_pt[1] + (-offset if side == "n" else offset)
        line_color = _net_color(net) if net else edge_color
        pygame.draw.line(surface, line_color, (px, py), edge_pt, 1)
        rect = (px - 4, py - 4, 8, 8)
        pygame.draw.rect(surface, pad_color, rect, 1)
        if net is None:
            color = unused_color
        else:
            color = in_color if kind == "in" else out_color
        pygame.draw.rect(surface, color, (rect[0] + 1, rect[1] + 1, rect[2] - 2, rect[3] - 2))
        if name and font:
            label = font.render(name, True, color)
            surface.blit(label, (px + 6, py - label.get_height() // 2))


def _normalize_pads(io) -> list[tuple[object, str]]:
    if isinstance(io, list):
        return [(entry, getattr(entry, "kind", "in")) for entry in io]
    pads: list[tuple[object, str]] = []
    pads += [(entry, "in") for entry in io.get("in", [])]
    pads += [(entry, "out") for entry in io.get("out", [])]
    return pads


def _clamp_idx(track, offsets: list[int]) -> int:
    if not offsets:
        return 0
    if track is None:
        return 0
    return min(max(int(track), 0), len(offsets) - 1)


def _infer_pad_track(cb_state: dict, x: int, y: int, side: str, net: str | None) -> int | None:
    cell = cb_state.get((x, y, side))
    if not cell:
        return None
    if net:
        for tap in cell.taps:
            if tap.net == net:
                return tap.track
    if cell.taps:
        return cell.taps[0].track
    return None


def _infer_pad_pin(cb_state: dict, x: int, y: int, side: str, net: str | None) -> int | None:
    cell = cb_state.get((x, y, side))
    if not cell:
        return None
    if net:
        for tap in cell.taps:
            if tap.net == net:
                return tap.pin
    if cell.taps:
        return cell.taps[0].pin
    return None


def _has_cb_tap(cb_state: dict, x: int, y: int, side: str, track: int, net: str | None) -> bool:
    cell = cb_state.get((x, y, side))
    if not cell:
        return False
    for tap in cell.taps:
        if tap.track != track:
            continue
        if net is None or tap.net == net:
            return True
    return False


def _cb_box_edge_point(
    origin: tuple[int, int],
    cell: int,
    x: int,
    y: int,
    side: str,
    track_off: int,
    cb_half: int,
) -> tuple[int, int] | None:
    col = 2 * x + 1
    row = 2 * y + 1
    if side == "w":
        cb_col, cb_row = col - 1, row
    elif side == "e":
        cb_col, cb_row = col + 1, row
    elif side == "n":
        cb_col, cb_row = col, row - 1
    else:
        cb_col, cb_row = col, row + 1
    cb_cx, cb_cy = node_center(origin, cell, cb_col, cb_row)
    cell_half = cell // 2
    if side == "w":
        return (cb_cx - cell_half, cb_cy + track_off)
    if side == "e":
        return (cb_cx + cell_half, cb_cy + track_off)
    if side == "n":
        return (cb_cx + track_off, cb_cy - cell_half)
    if side == "s":
        return (cb_cx + track_off, cb_cy + cell_half)
    return None
