from __future__ import annotations

from typing import Callable

from .layout import (
    TRACKS,
    cb_size,
    clb_size,
    lattice_dims,
    node_center,
    sb_size,
    track_offsets,
)

Side = str
Connection = tuple[Side, int, Side, int]
Tap = tuple[Side, int, int]


def draw_tracks(
    surface,
    origin: tuple[int, int],
    cell: int,
    grid_w: int,
    grid_h: int,
    font=None,
    show_labels: bool = False,
) -> None:
    import pygame

    x0, y0 = origin
    lattice_w, lattice_h = lattice_dims(grid_w, grid_h)
    line_color = (62, 66, 72)
    offsets = track_offsets(cell)

    for row in range(0, lattice_h, 2):
        for col in range(0, lattice_w - 2, 2):
            sx, sy = node_center(origin, cell, col, row)
            ex, _ = node_center(origin, cell, col + 2, row)
            sb_half = sb_size(cell) // 2
            for off in offsets:
                y = sy + off
                pygame.draw.line(surface, line_color, (sx + sb_half, y), (ex - sb_half, y), 1)
        if show_labels and font:
            sx, sy = node_center(origin, cell, 0, row)
            sb_half = sb_size(cell) // 2
            for idx, off in enumerate(offsets):
                text = font.render(f"T{idx}", True, (110, 110, 120))
                surface.blit(text, (sx - sb_half - text.get_width() - 4, sy + off - text.get_height() // 2))

    for col in range(0, lattice_w, 2):
        for row in range(0, lattice_h - 2, 2):
            sx, sy = node_center(origin, cell, col, row)
            _, ey = node_center(origin, cell, col, row + 2)
            sb_half = sb_size(cell) // 2
            for off in offsets:
                x = sx + off
                pygame.draw.line(surface, line_color, (x, sy + sb_half), (x, ey - sb_half), 1)
        if show_labels and font:
            sx, sy = node_center(origin, cell, col, 0)
            sb_half = sb_size(cell) // 2
            for idx, off in enumerate(offsets):
                text = font.render(f"T{idx}", True, (110, 110, 120))
                surface.blit(text, (sx + off - text.get_width() // 2, sy - sb_half - text.get_height() - 2))


def draw_switch_boxes(
    surface,
    origin: tuple[int, int],
    cell: int,
    grid_w: int,
    grid_h: int,
    font,
    show_labels: bool = True,
    connections_for: Callable[[int, int], list[Connection]] | None = None,
) -> None:
    import pygame

    lattice_w, lattice_h = lattice_dims(grid_w, grid_h)
    size = sb_size(cell)
    color = (90, 96, 106)

    for row in range(0, lattice_h, 2):
        for col in range(0, lattice_w, 2):
            cx, cy = node_center(origin, cell, col, row)
            rect = (cx - size // 2, cy - size // 2, size, size)
            pygame.draw.rect(surface, color, rect, 1)
            if show_labels:
                label = font.render(f"sb x{col//2}y{row//2}", True, (120, 120, 130))
                surface.blit(label, (cx - size // 2 + 1, cy - size // 2 - 10))
            _draw_box_tracks(surface, (cx, cy), size, cell, (72, 78, 86))
            _draw_wilton(surface, (cx, cy), size, cell, (72, 78, 86))
            if connections_for:
                _draw_connections(
                    surface,
                    (cx, cy),
                    size,
                    cell,
                    connections_for(col, row),
                )


def draw_connection_boxes(
    surface,
    origin: tuple[int, int],
    cell: int,
    grid_w: int,
    grid_h: int,
    font,
    pins_per_side: int,
    show_labels: bool = True,
    taps_for: Callable[[int, int, Side], list[Tap]] | None = None,
) -> None:
    import pygame

    size = cb_size(cell)
    color = (90, 96, 106)
    for y in range(grid_h):
        for x in range(grid_w):
            row = 2 * y + 1
            col = 2 * x + 1
            cx, cy = node_center(origin, cell, col, row)
            cb_left = (col - 1, row)
            cb_right = (col + 1, row)
            cb_top = (col, row - 1)
            cb_bottom = (col, row + 1)
            _draw_clb_to_cb_stubs(
                surface,
                (cx, cy),
                node_center(origin, cell, *cb_left),
                node_center(origin, cell, *cb_right),
                node_center(origin, cell, *cb_top),
                node_center(origin, cell, *cb_bottom),
                cell,
                pins_per_side,
            )
            for cb_col, cb_row in (cb_left, cb_right, cb_top, cb_bottom):
                px, py = node_center(origin, cell, cb_col, cb_row)
                rect = (px - size // 2, py - size // 2, size, size)
                pygame.draw.rect(surface, color, rect, 1)
                side = _cb_side(col, row, cb_col, cb_row)
                if show_labels:
                    label = font.render(f"cb x{x}y{y}.{side}", True, (120, 120, 130))
                    lx, ly = _cb_label_pos(rect, label, side)
                    surface.blit(label, (lx, ly))
                _draw_cb_tracks(surface, (px, py), size, cell, side, (72, 78, 86))
                if taps_for:
                    _draw_cb_taps(
                        surface,
                        (px, py),
                        size,
                        cell,
                        taps_for(cb_col, cb_row, side),
                        (cx, cy),
                        side,
                        pins_per_side,
                    )


def draw_clbs(
    surface,
    origin: tuple[int, int],
    cell: int,
    grid_w: int,
    grid_h: int,
    font,
    pins_per_side: int,
    show_labels: bool = True,
) -> None:
    import pygame

    size = clb_size(cell)
    inset = (cell - size) // 2
    pin_offs_w = _pin_offsets_for_side(size, pins_per_side, "w")
    pin_offs_e = _pin_offsets_for_side(size, pins_per_side, "e")
    pin_offs_n = _pin_offsets_for_side(size, pins_per_side, "n")
    pin_offs_s = _pin_offsets_for_side(size, pins_per_side, "s")
    for y in range(grid_h):
        for x in range(grid_w):
            row = 2 * y + 1
            col = 2 * x + 1
            x0, y0 = origin
            rect = (x0 + col * cell + inset, y0 + row * cell + inset, size, size)
            pygame.draw.rect(surface, (46, 48, 54), rect)
            pygame.draw.rect(surface, (90, 96, 106), rect, 1)
            if show_labels:
                label = font.render(f"x{x}y{y}", True, (150, 150, 160))
                surface.blit(label, (rect[0] + 5, rect[1] + 5))
            else:
                label = font.render("CLB", True, (150, 150, 160))
                surface.blit(label, (rect[0] + 5, rect[1] + 5))
            _draw_clb_pin_labels(
                surface,
                rect,
                pin_offs_w,
                pin_offs_e,
                pin_offs_n,
                pin_offs_s,
                font,
            )


def draw_route_polyline(
    surface, points: list[tuple[int, int]], color: tuple[int, int, int]
) -> None:
    import pygame

    for idx in range(len(points) - 1):
        _draw_manhattan(surface, points[idx], points[idx + 1], color)


def _draw_manhattan(
    surface, start: tuple[int, int], end: tuple[int, int], color: tuple[int, int, int]
) -> None:
    import pygame

    sx, sy = start
    ex, ey = end
    mid = (ex, sy)
    pygame.draw.line(surface, color, start, mid, 1)
    pygame.draw.line(surface, color, mid, end, 1)
    pygame.draw.rect(surface, color, (mid[0] - 2, mid[1] - 2, 4, 4))


def _draw_box_tracks(
    surface,
    center: tuple[int, int],
    size: int,
    cell: int,
    color: tuple[int, int, int],
) -> None:
    import pygame

    cx, cy = center
    half = size // 2
    offsets = track_offsets(cell)
    for off in offsets:
        pygame.draw.line(surface, color, (cx - half, cy + off), (cx + half, cy + off), 1)
        pygame.draw.line(surface, color, (cx + off, cy - half), (cx + off, cy + half), 1)


def _draw_connections(
    surface,
    center: tuple[int, int],
    size: int,
    cell: int,
    connections: list[Connection],
) -> None:
    import pygame

    if not connections:
        return
    offsets = track_offsets(cell)
    white = (235, 235, 235)
    for side_a, idx_a, side_b, idx_b in connections:
        pa = _box_track_point(center, size, offsets, side_a, idx_a)
        pb = _box_track_point(center, size, offsets, side_b, idx_b)
        if pa is None or pb is None:
            continue
        pygame.draw.line(surface, white, pa, pb, 1)
        _draw_sb_channel_stubs(surface, center, size, cell, offsets, side_a, idx_a, white)
        _draw_sb_channel_stubs(surface, center, size, cell, offsets, side_b, idx_b, white)


def _box_track_point(
    center: tuple[int, int],
    size: int,
    offsets: list[int],
    side: Side,
    track: int,
) -> tuple[int, int] | None:
    cx, cy = center
    half = size // 2
    idx = min(max(track, 0), len(offsets) - 1)
    off = offsets[idx]
    if side == "n":
        return (cx + off, cy - half)
    if side == "s":
        return (cx + off, cy + half)
    if side == "w":
        return (cx - half, cy + off)
    if side == "e":
        return (cx + half, cy + off)
    return None


def _draw_cb_taps(
    surface,
    center: tuple[int, int],
    size: int,
    cell: int,
    taps: list[Tap],
    clb_center: tuple[int, int],
    side: Side,
    pins_per_side: int,
) -> None:
    import pygame

    if not taps:
        return
    track_offs = track_offsets(cell)
    pin_offs = _pin_offsets_for_side(clb_size(cell), pins_per_side, side)
    white = (235, 235, 235)
    cx, cy = center
    cb_half = size // 2
    clb_half = clb_size(cell) // 2
    clb_x, clb_y = clb_center

    for tap_side, track, pin in taps:
        if tap_side != side:
            continue
        tidx = min(max(track, 0), len(track_offs) - 1)
        pidx = min(max(pin, 0), len(pin_offs) - 1)
        track_off = track_offs[tidx]
        pin_off = pin_offs[pidx]
        if side == "w":
            ix = cx + track_off
            iy = cy + pin_off
            cb_edge = (cx + cb_half, cy + pin_off)
            clb_edge = (clb_x - clb_half, clb_y + pin_off)
            pygame.draw.line(surface, white, clb_edge, cb_edge, 1)
            pygame.draw.line(surface, white, cb_edge, (ix, iy), 1)
            pygame.draw.line(surface, white, (ix, cy - cb_half), (ix, cy + cb_half), 1)
            _draw_cb_lane_extensions(surface, cx, cy, cb_half, cell // 2, "v", track_off, white)
        elif side == "e":
            ix = cx + track_off
            iy = cy + pin_off
            cb_edge = (cx - cb_half, cy + pin_off)
            clb_edge = (clb_x + clb_half, clb_y + pin_off)
            pygame.draw.line(surface, white, clb_edge, cb_edge, 1)
            pygame.draw.line(surface, white, cb_edge, (ix, iy), 1)
            pygame.draw.line(surface, white, (ix, cy - cb_half), (ix, cy + cb_half), 1)
            _draw_cb_lane_extensions(surface, cx, cy, cb_half, cell // 2, "v", track_off, white)
        elif side == "n":
            ix = cx + pin_off
            iy = cy + track_off
            cb_edge = (cx + pin_off, cy + cb_half)
            clb_edge = (clb_x + pin_off, clb_y - clb_half)
            pygame.draw.line(surface, white, clb_edge, cb_edge, 1)
            pygame.draw.line(surface, white, cb_edge, (ix, iy), 1)
            pygame.draw.line(surface, white, (cx - cb_half, iy), (cx + cb_half, iy), 1)
            _draw_cb_lane_extensions(surface, cx, cy, cb_half, cell // 2, "h", track_off, white)
        else:
            ix = cx + pin_off
            iy = cy + track_off
            cb_edge = (cx + pin_off, cy - cb_half)
            clb_edge = (clb_x + pin_off, clb_y + clb_half)
            pygame.draw.line(surface, white, clb_edge, cb_edge, 1)
            pygame.draw.line(surface, white, cb_edge, (ix, iy), 1)
            pygame.draw.line(surface, white, (cx - cb_half, iy), (cx + cb_half, iy), 1)
            _draw_cb_lane_extensions(surface, cx, cy, cb_half, cell // 2, "h", track_off, white)
        _draw_x(surface, (ix, iy), white)


def _draw_sb_channel_stubs(
    surface,
    center: tuple[int, int],
    size: int,
    cell: int,
    offsets: list[int],
    side: Side,
    track: int,
    color: tuple[int, int, int],
) -> None:
    import pygame

    cx, cy = center
    half = size // 2
    gap = _neighbor_gap(cell, size)
    idx = min(max(track, 0), len(offsets) - 1)
    off = offsets[idx]
    if side == "n":
        pygame.draw.line(surface, color, (cx + off, cy - half), (cx + off, cy - half - gap), 1)
    if side == "s":
        pygame.draw.line(surface, color, (cx + off, cy + half), (cx + off, cy + half + gap), 1)
    if side == "w":
        pygame.draw.line(surface, color, (cx - half, cy + off), (cx - half - gap, cy + off), 1)
    if side == "e":
        pygame.draw.line(surface, color, (cx + half, cy + off), (cx + half + gap, cy + off), 1)


def _neighbor_gap(cell: int, size: int) -> int:
    return max(2, (cell - size) // 2)


def _cb_side(col: int, row: int, cb_col: int, cb_row: int) -> Side:
    if cb_col < col:
        return "w"
    if cb_col > col:
        return "e"
    if cb_row < row:
        return "n"
    return "s"


def _pin_offsets_for_side(size: int, pins_per_side: int, side: Side) -> list[int]:
    count = max(1, pins_per_side)
    span = int(size * 0.6)
    if count == 1:
        return [0]
    start = -span // 2
    step = span / (count - 1)
    shift = step / 2 if side in ("e", "s") else 0.0
    limit = span // 2
    offsets = [int(start + i * step + shift) for i in range(count)]
    return [max(-limit, min(limit, off)) for off in offsets]


def _draw_x(surface, center: tuple[int, int], color: tuple[int, int, int]) -> None:
    import pygame

    cx, cy = center
    pygame.draw.line(surface, color, (cx - 2, cy - 2), (cx + 2, cy + 2), 1)
    pygame.draw.line(surface, color, (cx - 2, cy + 2), (cx + 2, cy - 2), 1)


def _draw_cb_lane_extensions(
    surface,
    cx: int,
    cy: int,
    cb_half: int,
    cell_half: int,
    orient: str,
    track_off: int,
    color: tuple[int, int, int],
) -> None:
    import pygame

    if orient == "v":
        x = cx + track_off
        pygame.draw.line(surface, color, (x, cy - cell_half), (x, cy - cb_half), 1)
        pygame.draw.line(surface, color, (x, cy + cb_half), (x, cy + cell_half), 1)
    else:
        y = cy + track_off
        pygame.draw.line(surface, color, (cx - cell_half, y), (cx - cb_half, y), 1)
        pygame.draw.line(surface, color, (cx + cb_half, y), (cx + cell_half, y), 1)


def _draw_clb_pin_labels(
    surface,
    rect: tuple[int, int, int, int],
    pin_offs_w: list[int],
    pin_offs_e: list[int],
    pin_offs_n: list[int],
    pin_offs_s: list[int],
    font,
) -> None:
    import pygame

    x, y, w, h = rect
    cx = x + w // 2
    cy = y + h // 2
    label_color = (140, 140, 150)
    for idx, off in enumerate(pin_offs_w):
        text = font.render(f"I{idx}", True, label_color)
        surface.blit(text, (x - 18, cy + off - text.get_height() // 2))
    for idx, off in enumerate(pin_offs_e):
        text = font.render(f"O{idx}", True, label_color)
        surface.blit(text, (x + w + 4, cy + off - text.get_height() // 2))
    for idx, off in enumerate(pin_offs_n):
        text = font.render(f"I{idx}", True, label_color)
        surface.blit(text, (cx + off - text.get_width() // 2, y - text.get_height() - 2))
    for idx, off in enumerate(pin_offs_s):
        text = font.render(f"O{idx}", True, label_color)
        surface.blit(text, (cx + off - text.get_width() // 2, y + h + 2))


def _cb_label_pos(
    rect: tuple[int, int, int, int],
    label,
    side: Side,
) -> tuple[int, int]:
    x, y, w, h = rect
    if side == "w":
        return (x + w + 4, y + 2)
    if side == "e":
        return (x - label.get_width() - 4, y + 2)
    if side == "n":
        return (x + 2, y + h + 2)
    return (x + 2, y - label.get_height() - 2)


def _draw_wilton(
    surface,
    center: tuple[int, int],
    size: int,
    cell: int,
    color: tuple[int, int, int],
) -> None:
    import pygame

    cx, cy = center
    half = size // 2
    offsets = track_offsets(cell)
    tracks = len(offsets)
    for idx in range(tracks):
        nxt = (idx + 1) % tracks
        prv = (idx - 1) % tracks
        north = (cx + offsets[idx], cy - half)
        south = (cx + offsets[idx], cy + half)
        east = (cx + half, cy + offsets[idx])
        west = (cx - half, cy + offsets[idx])
        ne = (cx + half, cy + offsets[nxt])
        es = (cx + offsets[nxt], cy + half)
        sw = (cx - half, cy + offsets[prv])
        wn = (cx + offsets[prv], cy - half)
        pygame.draw.line(surface, color, north, ne, 1)
        pygame.draw.line(surface, color, east, es, 1)
        pygame.draw.line(surface, color, south, sw, 1)
        pygame.draw.line(surface, color, west, wn, 1)


def _draw_clb_to_cb_stubs(
    surface,
    clb_center: tuple[int, int],
    cb_left: tuple[int, int],
    cb_right: tuple[int, int],
    cb_top: tuple[int, int],
    cb_bottom: tuple[int, int],
    cell: int,
    pins_per_side: int,
) -> None:
    import pygame

    stub_color = (78, 84, 92)
    clb_half = clb_size(cell) // 2
    cb_half = cb_size(cell) // 2
    cx, cy = clb_center
    pin_offs_w = _pin_offsets_for_side(clb_size(cell), pins_per_side, "w")
    pin_offs_e = _pin_offsets_for_side(clb_size(cell), pins_per_side, "e")
    pin_offs_n = _pin_offsets_for_side(clb_size(cell), pins_per_side, "n")
    pin_offs_s = _pin_offsets_for_side(clb_size(cell), pins_per_side, "s")
    left_edge = cx - clb_half
    right_edge = cx + clb_half
    top_edge = cy - clb_half
    bottom_edge = cy + clb_half

    for off in pin_offs_w:
        pygame.draw.line(
            surface,
            stub_color,
            (left_edge, cy + off),
            (cb_left[0] + cb_half, cy + off),
            1,
        )
    for off in pin_offs_e:
        pygame.draw.line(
            surface,
            stub_color,
            (right_edge, cy + off),
            (cb_right[0] - cb_half, cy + off),
            1,
        )
    for off in pin_offs_n:
        pygame.draw.line(
            surface,
            stub_color,
            (cx + off, top_edge),
            (cx + off, cb_top[1] + cb_half),
            1,
        )
    for off in pin_offs_s:
        pygame.draw.line(
            surface,
            stub_color,
            (cx + off, bottom_edge),
            (cx + off, cb_bottom[1] - cb_half),
            1,
        )


def _draw_cb_tracks(
    surface,
    center: tuple[int, int],
    size: int,
    cell: int,
    side: Side,
    color: tuple[int, int, int],
) -> None:
    import pygame

    cx, cy = center
    half = size // 2
    cell_half = cell // 2
    offsets = track_offsets(cell)
    if side in ("w", "e"):
        for off in offsets:
            x = cx + off
            pygame.draw.line(surface, color, (x, cy - cell_half), (x, cy - half), 1)
            pygame.draw.line(surface, color, (x, cy - half), (x, cy + half), 1)
            pygame.draw.line(surface, color, (x, cy + half), (x, cy + cell_half), 1)
    else:
        for off in offsets:
            y = cy + off
            pygame.draw.line(surface, color, (cx - cell_half, y), (cx - half, y), 1)
            pygame.draw.line(surface, color, (cx - half, y), (cx + half, y), 1)
            pygame.draw.line(surface, color, (cx + half, y), (cx + cell_half, y), 1)
