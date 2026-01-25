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
    show_internals: bool = False,
    slices_per_clb: int = 4,
    lut_k: int = 4,
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
            if show_internals:
                _draw_clb_internals(
                    surface,
                    rect,
                    font,
                    pins_per_side,
                    slices_per_clb,
                    lut_k,
                    pin_offs_w,
                    pin_offs_e,
                    pin_offs_n,
                    pin_offs_s,
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


def _xbar_tap_positions(
    rect: tuple[int, int, int, int],
    side_a: list[int],
    side_b: list[int],
) -> dict[tuple[str, int], tuple[int, int]]:
    x, y, w, h = rect
    taps: dict[tuple[str, int], tuple[int, int]] = {}
    for idx, off in enumerate(side_a):
        ty = int(y + (idx + 1) * h / (len(side_a) + 1))
        taps[("w", off)] = (x, ty)
        taps[("e", off)] = (x + w, ty)
    for idx, off in enumerate(side_b):
        tx = int(x + (idx + 1) * w / (len(side_b) + 1))
        ty_n = int(y + (idx + 1) * h / (len(side_b) + 1))
        ty_s = int(y + h - (idx + 1) * h / (len(side_b) + 1))
        taps[("n", off)] = (tx, ty_n)
        taps[("s", off)] = (tx, ty_s)
    return taps


def _draw_clb_internals(
    surface,
    rect: tuple[int, int, int, int],
    font,
    pins_per_side: int,
    slices_per_clb: int,
    lut_k: int,
    pin_offs_w: list[int],
    pin_offs_e: list[int],
    pin_offs_n: list[int],
    pin_offs_s: list[int],
) -> None:
    import pygame
    import math

    x, y, w, h = rect
    pad = max(3, w // 20)
    inner = (x + pad, y + pad, w - pad * 2, h - pad * 2)
    slice_count = max(1, slices_per_clb)
    cols = max(1, int(math.ceil(math.sqrt(slice_count))))
    rows = max(1, int(math.ceil(slice_count / cols)))
    # Input crossbar (shared) on the left side of the CLB interior.
    xbar_w = max(10, int(w * 0.12))
    in_xbar_rect = (int(inner[0]), int(inner[1]), xbar_w, int(inner[3]))
    pygame.draw.rect(surface, (70, 78, 88), in_xbar_rect, 1)
    in_xbar_label = font.render("IMUX", True, (140, 140, 150))
    surface.blit(in_xbar_label, (in_xbar_rect[0] + 2, in_xbar_rect[1] + 2))

    # Output crossbar (shared) on the right side of the CLB interior.
    out_xbar_rect = (
        int(inner[0] + inner[2] - xbar_w),
        int(inner[1]),
        xbar_w,
        int(inner[3]),
    )
    pygame.draw.rect(surface, (70, 78, 88), out_xbar_rect, 1)
    xbar_label = font.render("OMUX", True, (140, 140, 150))
    surface.blit(xbar_label, (out_xbar_rect[0] + 2, out_xbar_rect[1] + 2))

    # CLB pin stubs into IMUX/OMUX with per-track tap points.
    pin_color = (100, 100, 110)
    in_taps = _xbar_tap_positions(in_xbar_rect, pin_offs_w, pin_offs_n)
    stagger_step = max(2, int(w * 0.01))
    total_w = len(pin_offs_w)
    for idx, py in enumerate(pin_offs_w):
        y_world = int(y + h // 2 + py)
        entry_y = int(in_xbar_rect[1] + in_xbar_rect[3] * 0.75 + idx * 2)
        entry_y = min(entry_y, in_xbar_rect[1] + in_xbar_rect[3] - 3)
        jog_x = x + (total_w - idx) * stagger_step
        pygame.draw.line(surface, pin_color, (x, y_world), (jog_x, y_world), 1)
        pygame.draw.line(surface, pin_color, (jog_x, y_world), (jog_x, entry_y), 1)
        pygame.draw.line(surface, pin_color, (jog_x, entry_y), (in_xbar_rect[0], entry_y), 1)
    total_n = len(pin_offs_n)
    for idx, px_off in enumerate(pin_offs_n):
        x_world = int(x + w // 2 + px_off)
        tap = in_taps.get(("n", px_off))
        if tap:
            tx, ty = tap
            top_y = y
            jog_y = y + (idx + 1) * stagger_step
            entry_x = int(in_xbar_rect[0] + in_xbar_rect[2] * 0.25 + idx * 2)
            entry_x = max(in_xbar_rect[0] + 2, min(entry_x, in_xbar_rect[0] + in_xbar_rect[2] - 2))
            pygame.draw.line(surface, pin_color, (x_world, top_y), (x_world, jog_y), 1)
            pygame.draw.line(surface, pin_color, (x_world, jog_y), (entry_x, jog_y), 1)
            pygame.draw.line(surface, pin_color, (entry_x, jog_y), (entry_x, in_xbar_rect[1]), 1)

    total_e = len(pin_offs_e)
    for idx, py in enumerate(pin_offs_e):
        y_world = int(y + h // 2 + py)
        entry_y = int(out_xbar_rect[1] + out_xbar_rect[3] * 0.75 + idx * 2)
        entry_y = min(entry_y, out_xbar_rect[1] + out_xbar_rect[3] - 3)
        jog_x = x + w - (total_e - idx) * stagger_step
        xbar_right = out_xbar_rect[0] + out_xbar_rect[2]
        pygame.draw.line(surface, pin_color, (x + w, y_world), (jog_x, y_world), 1)
        pygame.draw.line(surface, pin_color, (jog_x, y_world), (jog_x, entry_y), 1)
        pygame.draw.line(surface, pin_color, (jog_x, entry_y), (xbar_right, entry_y), 1)
    out_taps = _xbar_tap_positions(out_xbar_rect, pin_offs_e, pin_offs_s)
    total_s = len(pin_offs_s)
    for idx, px_off in enumerate(pin_offs_s):
        x_world = int(x + w // 2 + px_off)
        tap = out_taps.get(("s", px_off))
        if tap:
            omux_bottom = out_xbar_rect[1] + out_xbar_rect[3]
            jog_y = y + h - (total_s - idx) * stagger_step
            entry_x = int(out_xbar_rect[0] + out_xbar_rect[2] * 0.25 + idx * 2)
            entry_x = max(out_xbar_rect[0] + 2, min(entry_x, out_xbar_rect[0] + out_xbar_rect[2] - 2))
            pygame.draw.line(surface, pin_color, (x_world, y + h), (x_world, jog_y), 1)
            pygame.draw.line(surface, pin_color, (x_world, jog_y), (entry_x, jog_y), 1)
            pygame.draw.line(surface, pin_color, (entry_x, jog_y), (entry_x, omux_bottom), 1)

    slice_area = (
        in_xbar_rect[0] + in_xbar_rect[2],
        inner[1],
        inner[2] - (in_xbar_rect[2] + out_xbar_rect[2]),
        inner[3],
    )
    slice_w = slice_area[2] / cols if cols else inner[2]
    slice_h = slice_area[3] / rows if rows else inner[3]
    slice_pad = max(2, int(min(slice_w, slice_h) * 0.08))
    lut_inputs = max(1, lut_k)

    for idx in range(slice_count):
        r = idx // cols
        c = idx % cols
        sx = slice_area[0] + c * slice_w + slice_pad
        sy = slice_area[1] + r * slice_h + slice_pad
        sw = slice_w - slice_pad * 2
        sh = slice_h - slice_pad * 2
        slice_rect = (int(sx), int(sy), int(sw), int(sh))
        pygame.draw.rect(surface, (62, 68, 78), slice_rect, 1)
        slice_label = font.render(f"S{idx}", True, (140, 140, 150))
        surface.blit(slice_label, (slice_rect[0] + 2, slice_rect[1] + 2))
        lut_w = int(sw * 0.6)
        ff_w = int(sw * 0.22)
        box_h = int(sh)
        imux_w = max(6, int(sw * 0.12))
        imux_x = int(sx)
        imux_rect = (imux_x, int(sy + sh * 0.2), imux_w, int(sh * 0.6))
        lut_rect = (int(imux_rect[0] + imux_w + slice_pad), int(sy), lut_w - slice_pad, box_h)
        ff_h = int(box_h * 0.5)
        ff_rect = (int(sx + sw - ff_w), int(sy + box_h - ff_h), ff_w, ff_h)
        mux_x = ff_rect[0] + ff_rect[2] + max(1, slice_pad // 2)
        mid_y = int(sy + box_h // 2)
        ff_mid_y = int(ff_rect[1] + ff_rect[3] * 0.5)
        pass_y = int(sy + box_h * 0.3)

        pygame.draw.rect(surface, (70, 78, 88), lut_rect, 1)
        pygame.draw.rect(surface, (70, 78, 88), ff_rect, 1)
        pygame.draw.rect(surface, (70, 78, 88), imux_rect, 1)
        lut_label = font.render("LUT", True, (160, 160, 170))
        ff_label = font.render("FF", True, (160, 160, 170))
        imux_label = font.render("IM", True, (160, 160, 170))
        surface.blit(lut_label, (lut_rect[0] + 2, lut_rect[1] + 2))
        surface.blit(ff_label, (ff_rect[0] + 2, ff_rect[1] + 2))
        surface.blit(imux_label, (imux_rect[0] + 1, imux_rect[1] + 2))

        lut_out_x = lut_rect[0] + lut_rect[2]
        ff_in_x = ff_rect[0]
        ff_out_x = ff_rect[0] + ff_rect[2]
        # IN XBAR -> IMUX
        pygame.draw.line(
            surface,
            (100, 100, 110),
            (in_xbar_rect[0] + in_xbar_rect[2], mid_y),
            (imux_rect[0], mid_y),
            1,
        )
        # IMUX -> LUT input
        pygame.draw.line(
            surface,
            (120, 120, 130),
            (imux_rect[0] + imux_rect[2], mid_y),
            (lut_rect[0], mid_y),
            1,
        )
        pygame.draw.line(surface, (120, 120, 130), (lut_out_x, ff_mid_y), (ff_in_x, ff_mid_y), 1)
        pygame.draw.line(surface, (120, 120, 130), (ff_out_x, ff_mid_y), (mux_x, ff_mid_y), 1)
        pygame.draw.line(surface, (120, 120, 130), (lut_out_x, pass_y), (mux_x, pass_y), 1)

        mux_h = min(8, int(sh * 0.2))
        mux_cy = int((ff_mid_y + pass_y) / 2)
        mux_pts = [
            (mux_x, mux_cy - mux_h),
            (mux_x, mux_cy + mux_h),
            (mux_x + mux_h, mux_cy),
        ]
        pygame.draw.polygon(surface, (120, 120, 130), mux_pts, 1)

        # Converge both paths into the mux and a single output.
        pygame.draw.line(surface, (120, 120, 130), (mux_x, pass_y), (mux_x, mux_cy), 1)
        pygame.draw.line(surface, (120, 120, 130), (mux_x, ff_mid_y), (mux_x, mux_cy), 1)
        pygame.draw.line(
            surface,
            (120, 120, 130),
            (mux_x + mux_h, mux_cy),
            (out_xbar_rect[0], mux_cy),
            1,
        )

        _draw_lut_table(surface, lut_rect, font, lut_inputs)

    # Output pins are drawn via OMUX routing above.


def _draw_lut_table(
    surface,
    rect: tuple[int, int, int, int],
    font,
    lut_inputs: int,
) -> None:
    import pygame

    x, y, w, h = rect
    rows = 2 ** lut_inputs
    cols = lut_inputs + 1  # inputs + output
    lut_header_h = 12
    col_header_h = 12
    table_y = y + lut_header_h + col_header_h + 3
    table_h = h - lut_header_h - col_header_h - 5
    if rows <= 0 or table_h <= 4:
        return

    row_h = table_h / rows
    col_w = w / cols
    if row_h < 6 or col_w < 6:
        return

    grid_color = (80, 86, 96)
    for r in range(rows + 1):
        yy = int(table_y + r * row_h)
        pygame.draw.line(surface, grid_color, (x + 2, yy), (x + w - 2, yy), 1)
    for c in range(cols + 1):
        xx = int(x + c * col_w)
        pygame.draw.line(surface, grid_color, (xx, table_y), (xx, table_y + table_h), 1)

    # Column header labels
    for c in range(lut_inputs):
        label = font.render(f"I{c}", True, (150, 150, 160))
        surface.blit(label, (int(x + c * col_w + 3), y + lut_header_h + 2))
    out_label = font.render("O", True, (150, 150, 160))
    surface.blit(out_label, (int(x + lut_inputs * col_w + 3), y + lut_header_h + 2))

    # Truth table contents (default zeros)
    for r in range(rows):
        bits = format(r, f"0{lut_inputs}b")
        for c in range(lut_inputs):
            val = font.render(bits[c], True, (140, 140, 150))
            vx = int(x + c * col_w + col_w / 2 - val.get_width() / 2)
            vy = int(table_y + r * row_h + row_h / 2 - val.get_height() / 2)
            surface.blit(val, (vx, vy))
        out = font.render("0", True, (140, 140, 150))
        ox = int(x + lut_inputs * col_w + col_w / 2 - out.get_width() / 2)
        oy = int(table_y + r * row_h + row_h / 2 - out.get_height() / 2)
        surface.blit(out, (ox, oy))

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
