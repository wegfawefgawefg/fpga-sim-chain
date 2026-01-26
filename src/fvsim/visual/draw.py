from __future__ import annotations

from typing import Callable

from .layout import cb_size, clb_size, lattice_dims, node_center, sb_size, track_offsets

Side = str
Connection = tuple[Side, int, Side, int] | tuple[Side, int, Side, int, str]
Tap = tuple[Side, int, int] | tuple[Side, int, int, str]


def draw_tracks(
    surface,
    origin: tuple[int, int],
    cell: int,
    grid_w: int,
    grid_h: int,
    font=None,
    show_labels: bool = False,
    tracks: int = 4,
    track_dirs: dict[str, int] | None = None,
    routing_dir: str = "bi",
) -> None:
    import pygame

    x0, y0 = origin
    lattice_w, lattice_h = lattice_dims(grid_w, grid_h)
    line_color = (62, 66, 72)
    offsets_h = track_offsets(cell, tracks, track_dirs, "h", routing_dir)
    offsets_v = track_offsets(cell, tracks, track_dirs, "v", routing_dir)

    for row in range(0, lattice_h, 2):
        for col in range(0, lattice_w - 2, 2):
            sx, sy = node_center(origin, cell, col, row)
            ex, _ = node_center(origin, cell, col + 2, row)
            sb_half = sb_size(cell) // 2
            for off in offsets_h:
                y = sy + off
                pygame.draw.line(surface, line_color, (sx + sb_half, y), (ex - sb_half, y), 1)
        if show_labels and font:
            sx, sy = node_center(origin, cell, 0, row)
            sb_half = sb_size(cell) // 2
            for idx, off in enumerate(offsets_h):
                label = _lane_label(idx, "h", track_dirs, routing_dir)
                text = font.render(label, True, (110, 110, 120))
                surface.blit(text, (sx - sb_half - text.get_width() - 4, sy + off - text.get_height() // 2))

    for col in range(0, lattice_w, 2):
        for row in range(0, lattice_h - 2, 2):
            sx, sy = node_center(origin, cell, col, row)
            _, ey = node_center(origin, cell, col, row + 2)
            sb_half = sb_size(cell) // 2
            for off in offsets_v:
                x = sx + off
                pygame.draw.line(surface, line_color, (x, sy + sb_half), (x, ey - sb_half), 1)
        if show_labels and font:
            sx, sy = node_center(origin, cell, col, 0)
            sb_half = sb_size(cell) // 2
            for idx, off in enumerate(offsets_v):
                label = _lane_label(idx, "v", track_dirs, routing_dir)
                text = font.render(label, True, (110, 110, 120))
                surface.blit(text, (sx + off - text.get_width() // 2, sy - sb_half - text.get_height() - 2))


def draw_switch_boxes(
    surface,
    origin: tuple[int, int],
    cell: int,
    grid_w: int,
    grid_h: int,
    font,
    show_labels: bool = True,
    tracks: int = 4,
    track_dirs: dict[str, int] | None = None,
    routing_dir: str = "bi",
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
            offsets_h = track_offsets(cell, tracks, track_dirs, "h", routing_dir)
            offsets_v = track_offsets(cell, tracks, track_dirs, "v", routing_dir)
            _draw_box_tracks(surface, (cx, cy), size, offsets_h, offsets_v, (72, 78, 86))
            _draw_wilton(surface, (cx, cy), size, offsets_h, offsets_v, (72, 78, 86))
            if connections_for:
                _draw_connections(
                    surface,
                    (cx, cy),
                    size,
                    offsets_h,
                    offsets_v,
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
    tracks: int = 4,
    track_dirs: dict[str, int] | None = None,
    routing_dir: str = "bi",
    taps_for: Callable[[int, int, Side], list[Tap]] | None = None,
) -> None:
    import pygame

    size = cb_size(cell)
    color = (90, 96, 106)
    offsets_h = track_offsets(cell, tracks, track_dirs, "h", routing_dir)
    offsets_v = track_offsets(cell, tracks, track_dirs, "v", routing_dir)
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
                _draw_cb_tracks(surface, (px, py), size, cell, side, offsets_h, offsets_v, (72, 78, 86))
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
                        offsets_h,
                        offsets_v,
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
    tick: int = 0,
    lut_tables: dict[tuple[int, int, int], list[int]] | None = None,
    rng=None,
    omux_maps: dict[tuple[int, int], list[tuple[str, int, bool]]] | None = None,
    imux_maps: dict[tuple[int, int], list[list[str]]] | None = None,
    ff_state: dict[tuple[int, int, int], dict[str, int]] | None = None,
    inputs: list[int] | None = None,
    clb_config: dict | None = None,
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
                    (x, y),
                    tick,
                    lut_tables,
                    rng,
                    omux_maps,
                    imux_maps,
                    ff_state,
                    inputs,
                    clb_config,
                )


def draw_route_polyline(
    surface, points: list[tuple[int, int]], color: tuple[int, int, int]
) -> None:
    import pygame

    for idx in range(len(points) - 1):
        _draw_manhattan(surface, points[idx], points[idx + 1], color)


def draw_route_arrow(
    surface,
    start: tuple[int, int],
    end: tuple[int, int],
    flow: str | None,
    color: tuple[int, int, int],
) -> None:
    import pygame
    import math

    if flow not in {"n", "s", "e", "w"}:
        return
    sx, sy = start
    ex, ey = end
    if flow in {"w", "n"}:
        sx, sy, ex, ey = ex, ey, sx, sy
    mx = (sx + ex) / 2
    my = (sy + ey) / 2
    dx = ex - sx
    dy = ey - sy
    length = math.hypot(dx, dy)
    if length <= 0.1:
        return
    ux, uy = dx / length, dy / length
    size = 6
    px, py = -uy, ux
    tip = (mx + ux * size, my + uy * size)
    left = (mx - ux * size + px * size * 0.6, my - uy * size + py * size * 0.6)
    right = (mx - ux * size - px * size * 0.6, my - uy * size - py * size * 0.6)
    pygame.draw.polygon(surface, color, [tip, left, right])


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


def _draw_alpha_line(
    surface,
    start: tuple[int, int],
    end: tuple[int, int],
    color: tuple[int, int, int],
    alpha: int = 140,
    width: int = 1,
) -> None:
    import pygame

    x0 = min(start[0], end[0]) - width
    y0 = min(start[1], end[1]) - width
    x1 = max(start[0], end[0]) + width
    y1 = max(start[1], end[1]) + width
    w = max(1, x1 - x0)
    h = max(1, y1 - y0)
    tmp = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.line(
        tmp,
        (color[0], color[1], color[2], alpha),
        (start[0] - x0, start[1] - y0),
        (end[0] - x0, end[1] - y0),
        width,
    )
    surface.blit(tmp, (x0, y0))


def _draw_alpha_circle(
    surface,
    center: tuple[int, int],
    radius: int,
    color: tuple[int, int, int],
    alpha: int = 140,
) -> None:
    import pygame

    x0 = center[0] - radius - 1
    y0 = center[1] - radius - 1
    size = radius * 2 + 2
    tmp = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(
        tmp, (color[0], color[1], color[2], alpha), (radius + 1, radius + 1), radius
    )
    surface.blit(tmp, (x0, y0))


def _draw_box_tracks(
    surface,
    center: tuple[int, int],
    size: int,
    offsets_h: list[int],
    offsets_v: list[int],
    color: tuple[int, int, int],
) -> None:
    import pygame

    cx, cy = center
    half = size // 2
    for off in offsets_h:
        pygame.draw.line(surface, color, (cx - half, cy + off), (cx + half, cy + off), 1)
    for off in offsets_v:
        pygame.draw.line(surface, color, (cx + off, cy - half), (cx + off, cy + half), 1)


def _draw_connections(
    surface,
    center: tuple[int, int],
    size: int,
    offsets_h: list[int],
    offsets_v: list[int],
    cell: int,
    connections: list[Connection],
) -> None:
    import pygame

    if not connections:
        return
    white = (235, 235, 235)
    for conn in connections:
        if len(conn) == 5:
            side_a, idx_a, side_b, idx_b, net = conn
            color = _net_color(net)
        else:
            side_a, idx_a, side_b, idx_b = conn
            color = white
        offsets_a = _offsets_for_side(side_a, offsets_h, offsets_v)
        offsets_b = _offsets_for_side(side_b, offsets_h, offsets_v)
        pa = _box_track_point(center, size, offsets_a, side_a, idx_a)
        pb = _box_track_point(center, size, offsets_b, side_b, idx_b)
        if pa is None or pb is None:
            continue
        pygame.draw.line(surface, color, pa, pb, 1)
        _draw_sb_channel_stubs(
            surface, center, size, offsets_h, offsets_v, cell, side_a, idx_a, color
        )
        _draw_sb_channel_stubs(
            surface, center, size, offsets_h, offsets_v, cell, side_b, idx_b, color
        )


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
    offsets_h: list[int],
    offsets_v: list[int],
) -> None:
    import pygame

    if not taps:
        return
    track_offs = _offsets_for_side(side, offsets_h, offsets_v)
    pin_offs = _pin_offsets_for_side(clb_size(cell), pins_per_side, side)
    white = (235, 235, 235)
    cx, cy = center
    cb_half = size // 2
    clb_half = clb_size(cell) // 2
    clb_x, clb_y = clb_center

    for tap in taps:
        if len(tap) == 4:
            tap_side, track, pin, net = tap
            color = _net_color(net)
        else:
            tap_side, track, pin = tap
            color = white
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
            pygame.draw.line(surface, color, clb_edge, cb_edge, 1)
            pygame.draw.line(surface, color, cb_edge, (ix, iy), 1)
            pygame.draw.line(surface, color, (ix, cy - cb_half), (ix, cy + cb_half), 1)
            _draw_cb_lane_extensions(surface, cx, cy, cb_half, cell // 2, "v", track_off, color)
        elif side == "e":
            ix = cx + track_off
            iy = cy + pin_off
            cb_edge = (cx - cb_half, cy + pin_off)
            clb_edge = (clb_x + clb_half, clb_y + pin_off)
            pygame.draw.line(surface, color, clb_edge, cb_edge, 1)
            pygame.draw.line(surface, color, cb_edge, (ix, iy), 1)
            pygame.draw.line(surface, color, (ix, cy - cb_half), (ix, cy + cb_half), 1)
            _draw_cb_lane_extensions(surface, cx, cy, cb_half, cell // 2, "v", track_off, color)
        elif side == "n":
            ix = cx + pin_off
            iy = cy + track_off
            cb_edge = (cx + pin_off, cy + cb_half)
            clb_edge = (clb_x + pin_off, clb_y - clb_half)
            pygame.draw.line(surface, color, clb_edge, cb_edge, 1)
            pygame.draw.line(surface, color, cb_edge, (ix, iy), 1)
            pygame.draw.line(surface, color, (cx - cb_half, iy), (cx + cb_half, iy), 1)
            _draw_cb_lane_extensions(surface, cx, cy, cb_half, cell // 2, "h", track_off, color)
        else:
            ix = cx + pin_off
            iy = cy + track_off
            cb_edge = (cx + pin_off, cy - cb_half)
            clb_edge = (clb_x + pin_off, clb_y + clb_half)
            pygame.draw.line(surface, color, clb_edge, cb_edge, 1)
            pygame.draw.line(surface, color, cb_edge, (ix, iy), 1)
            pygame.draw.line(surface, color, (cx - cb_half, iy), (cx + cb_half, iy), 1)
            _draw_cb_lane_extensions(surface, cx, cy, cb_half, cell // 2, "h", track_off, color)
        _draw_x(surface, (ix, iy), color)


def _draw_sb_channel_stubs(
    surface,
    center: tuple[int, int],
    size: int,
    offsets_h: list[int],
    offsets_v: list[int],
    cell: int,
    side: Side,
    track: int,
    color: tuple[int, int, int],
) -> None:
    import pygame

    cx, cy = center
    half = size // 2
    gap = _neighbor_gap(cell, size)
    offsets = _offsets_for_side(side, offsets_h, offsets_v)
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


def _neighbor_gap_from_size(size: int) -> int:
    return max(2, size // 6)


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
        text = font.render(f"W{idx}", True, label_color)
        surface.blit(text, (x - 18, cy + off - text.get_height() // 2))
    for idx, off in enumerate(pin_offs_e):
        text = font.render(f"E{idx}", True, label_color)
        surface.blit(text, (x + w + 4, cy + off - text.get_height() // 2))
    for idx, off in enumerate(pin_offs_n):
        text = font.render(f"N{idx}", True, label_color)
        surface.blit(text, (cx + off - text.get_width() // 2, y - text.get_height() - 2))
    for idx, off in enumerate(pin_offs_s):
        text = font.render(f"S{idx}", True, label_color)
        surface.blit(text, (cx + off - text.get_width() // 2, y + h + 2))


def _net_color(net: str) -> tuple[int, int, int]:
    if not net:
        return (200, 200, 200)
    h = sum(ord(ch) for ch in net) % 360
    return _hsv_to_rgb(h / 360.0, 0.7, 0.9)


def _hsv_to_rgb(h: float, s: float, v: float) -> tuple[int, int, int]:
    i = int(h * 6)
    f = h * 6 - i
    p = v * (1 - s)
    q = v * (1 - f * s)
    t = v * (1 - (1 - f) * s)
    i = i % 6
    if i == 0:
        r, g, b = v, t, p
    elif i == 1:
        r, g, b = q, v, p
    elif i == 2:
        r, g, b = p, v, t
    elif i == 3:
        r, g, b = p, q, v
    elif i == 4:
        r, g, b = t, p, v
    else:
        r, g, b = v, p, q
    return (int(r * 255), int(g * 255), int(b * 255))


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
    clb_xy: tuple[int, int],
    tick: int,
    lut_tables: dict[tuple[int, int, int], list[int]] | None,
    rng,
    omux_maps: dict[tuple[int, int], list[tuple[str, int, bool]]] | None,
    imux_maps: dict[tuple[int, int], list[list[str]]] | None,
    ff_state: dict[tuple[int, int, int], dict[str, int]] | None,
    inputs: list[int] | None,
    clb_config: dict | None,
) -> None:
    import pygame
    import math

    x, y, w, h = rect
    pad = max(2, w // 30)
    inner = (x + pad, y + pad, w - pad * 2, h - pad * 2)
    slice_count = max(1, slices_per_clb)
    cols = max(1, int(math.ceil(math.sqrt(slice_count))))
    rows = max(1, int(math.ceil(slice_count / cols)))
    # Direct output taps at CLB edge pins.
    omux_e_taps: dict[int, tuple[int, int]] = {}
    if pin_offs_e:
        for idx, _off in enumerate(pin_offs_e):
            ty = int(y + h // 2 + pin_offs_e[idx])
            omux_e_taps[idx] = (x + w, ty)
    omux_s_taps: dict[int, tuple[int, int]] = {}
    if pin_offs_s:
        for idx, _off in enumerate(pin_offs_s):
            tx = int(x + w // 2 + pin_offs_s[idx])
            omux_s_taps[idx] = (tx, y + h)

    slice_area = inner
    slice_area_rect = (
        int(slice_area[0]),
        int(slice_area[1]),
        int(slice_area[2]),
        int(slice_area[3]),
    )
    pygame.draw.rect(surface, (58, 62, 72), slice_area_rect, 1)
    slice_area_label = font.render("SLICES", True, (120, 120, 130))
    surface.blit(slice_area_label, (slice_area_rect[0] + 2, slice_area_rect[1] + 2))
    slice_w = slice_area[2] / cols if cols else inner[2]
    slice_h = slice_area[3] / rows if rows else inner[3]
    slice_pad = max(1, int(min(slice_w, slice_h) * 0.05))
    lut_inputs = max(1, min(4, lut_k))
    rows = 2 ** lut_inputs
    if inputs is None:
        inputs = [0] * lut_inputs
    input_bits = inputs[:lut_inputs]
    active_idx = 0
    for i, bit in enumerate(input_bits):
        active_idx |= (bit & 1) << i

    clb_key = f"x{clb_xy[0]}y{clb_xy[1]}"
    clb_slices = clb_config.get(clb_key, {}).get("slices") if clb_config else None
    if clb_slices:
        slice_outputs = [None] * slice_count
        slice_inputs = [[] for _ in range(slice_count)]
        slice_tables = [None] * slice_count
        for entry in clb_slices:
            sidx = int(entry.get("index", 0))
            if sidx < 0 or sidx >= slice_count:
                continue
            out = entry.get("output", {})
            slice_outputs[sidx] = (
                out.get("side", "e"),
                int(out.get("pin", 0)),
                bool(out.get("use_ff", False)),
            )
            slice_inputs[sidx] = entry.get("inputs", [])
            slice_tables[sidx] = entry.get("table")
    elif omux_maps is not None and rng is not None:
        omux_key = (clb_xy[0], clb_xy[1])
        if omux_key not in omux_maps:
            outputs: list[tuple[str, int]] = []
            outputs += [("e", idx) for idx in range(len(pin_offs_e))]
            outputs += [("s", idx) for idx in range(len(pin_offs_s))]
            outputs += [("w", idx) for idx in range(len(pin_offs_w))]
            outputs += [("n", idx) for idx in range(len(pin_offs_n))]
            rng.shuffle(outputs)
            mapped: list[tuple[str, int, bool]] = []
            for out in outputs[:slice_count]:
                mapped.append((out[0], out[1], bool(rng.randint(0, 1))))
            omux_maps[omux_key] = mapped
        slice_outputs = omux_maps[omux_key]
    else:
        slice_outputs = [("e", idx, True) for idx in range(min(slice_count, len(pin_offs_e)))]

    if clb_slices:
        pass
    elif imux_maps is not None and rng is not None:
        imux_key = (clb_xy[0], clb_xy[1])
        if imux_key not in imux_maps:
            sources: list[str] = []
            sources += [f"W{i}" for i in range(len(pin_offs_w))]
            sources += [f"N{i}" for i in range(len(pin_offs_n))]
            sources += [f"E{i}" for i in range(len(pin_offs_e))]
            sources += [f"S{i}" for i in range(len(pin_offs_s))]
            mapped_inputs: list[list[str]] = []
            for _ in range(slice_count):
                if sources:
                    picks = [sources[rng.randint(0, len(sources) - 1)] for _ in range(lut_inputs)]
                else:
                    picks = [f"I{i}" for i in range(lut_inputs)]
                mapped_inputs.append(picks)
            imux_maps[imux_key] = mapped_inputs
        slice_inputs = imux_maps[imux_key]
    else:
        slice_inputs = [[f"I{i}" for i in range(lut_inputs)] for _ in range(slice_count)]

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
        inner_pad = max(2, int(min(sw, sh) * 0.04))
        lut_w = int(sw * 0.72)
        ff_w = int(sw * 0.14)
        box_h = int(sh - inner_pad * 2)
        lut_rect = (
            int(sx + inner_pad),
            int(sy + inner_pad),
            int(lut_w),
            box_h,
        )
        ff_h = ff_w
        ff_rect = (
            int(sx + sw - ff_w - inner_pad),
            int(sy + inner_pad + box_h - ff_h),
            ff_w,
            ff_h,
        )
        lut_rect = (
            lut_rect[0],
            lut_rect[1],
            min(lut_rect[2], ff_rect[0] - lut_rect[0] - inner_pad),
            lut_rect[3],
        )
        lut_in_taps: list[tuple[int, int]] = []
        lut_header_h = 12
        col_header_h = 12
        table_y = lut_rect[1] + lut_header_h + col_header_h + 3
        col_w = lut_rect[2] / (lut_inputs + 1)
        for i in range(lut_inputs):
            tx = int(lut_rect[0] + col_w * (i + 0.5))
            lut_in_taps.append((tx, table_y))

        pygame.draw.rect(surface, (70, 78, 88), lut_rect, 1)
        pygame.draw.rect(surface, (70, 78, 88), ff_rect, 1)
        lut_label = font.render("LUT", True, (160, 160, 170))
        ff_label = font.render("FF", True, (160, 160, 170))
        surface.blit(lut_label, (lut_rect[0] + 2, lut_rect[1] + 2))
        surface.blit(ff_label, (ff_rect[0] + 2, ff_rect[1] + 2))
        label_x = slice_rect[0] + slice_rect[2] - 2
        label_y = slice_rect[1] + 4
        lines: list[str] = []
        if idx < len(slice_outputs) and slice_outputs[idx]:
            side, pin_idx, use_ff = slice_outputs[idx]
            mode_tag = "F" if use_ff else "L"
            lines.append(f"O:{side}{pin_idx}{mode_tag}")
        if idx < len(slice_inputs):
            for in_idx, src in enumerate(slice_inputs[idx][:lut_inputs]):
                lines.append(f"I{in_idx}:{src}")
        for line in lines:
            text = font.render(line, True, (130, 130, 140))
            surface.blit(text, (label_x - text.get_width(), label_y))
            label_y += text.get_height() + 1

        input_line_color = (120, 130, 150)
        for in_idx, src in enumerate(slice_inputs[idx][:lut_inputs]):
            if in_idx >= len(lut_in_taps):
                continue
            tx, ty = lut_in_taps[in_idx]
            src_pt = None
            if src.startswith("W"):
                pidx = int(src[1:])
                if pidx < len(pin_offs_w):
                    src_pt = (x, int(y + h // 2 + pin_offs_w[pidx]))
            elif src.startswith("E"):
                pidx = int(src[1:])
                if pidx < len(pin_offs_e):
                    src_pt = (x + w, int(y + h // 2 + pin_offs_e[pidx]))
            elif src.startswith("N"):
                pidx = int(src[1:])
                if pidx < len(pin_offs_n):
                    src_pt = (int(x + w // 2 + pin_offs_n[pidx]), y)
            elif src.startswith("S"):
                pidx = int(src[1:])
                if pidx < len(pin_offs_s):
                    src_pt = (int(x + w // 2 + pin_offs_s[pidx]), y + h)
            if src_pt:
                _draw_alpha_line(surface, src_pt, (tx, ty), input_line_color, 90)

        if clb_slices:
            table = None
            if idx < len(slice_tables):
                table = slice_tables[idx]
        else:
            table_key = (clb_xy[0], clb_xy[1], idx)
            if lut_tables is not None and rng is not None:
                table = lut_tables.get(table_key)
                if table is None:
                    table = [rng.randint(0, 1) for _ in range(rows)]
                    lut_tables[table_key] = table
            else:
                table = None

        # Slice-local wiring omitted for clarity.
        if idx < len(slice_outputs) and slice_outputs[idx]:
            side, pin_idx, use_ff = slice_outputs[idx]
            tap = None
            if side == "e" and pin_idx < len(pin_offs_e):
                tap = omux_e_taps.get(pin_idx)
            elif side == "s" and pin_idx < len(pin_offs_s):
                tap = omux_s_taps.get(pin_idx)
            elif side == "w" and pin_idx < len(pin_offs_w):
                ty = int(y + h // 2 + pin_offs_w[pin_idx])
                tap = (x, ty)
            elif side == "n" and pin_idx < len(pin_offs_n):
                tx = int(x + w // 2 + pin_offs_n[pin_idx])
                tap = (tx, y)
            if tap:
                tx, ty = tap
                out_val = table[active_idx] if table is not None else 0
                display_val = out_val
                if use_ff:
                    ff_key = (clb_xy[0], clb_xy[1], idx)
                    if ff_state is not None:
                        state = ff_state.get(ff_key, {"val": 0, "tick": -1})
                        display_val = state.get("val", 0)
                        if state.get("tick") != tick:
                            ff_state[ff_key] = {"val": out_val, "tick": tick}
                    out_x = ff_rect[0] + ff_rect[2]
                    out_y = ff_rect[1] + ff_rect[3] // 2
                    pygame.draw.rect(
                        surface,
                        (70, 86, 110),
                        ff_rect,
                        0,
                    )
                    pygame.draw.rect(surface, (90, 96, 106), ff_rect, 1)
                    ff_text = font.render(str(display_val), True, (210, 210, 220))
                    surface.blit(
                        ff_text,
                        (
                            ff_rect[0] + (ff_rect[2] - ff_text.get_width()) // 2,
                            ff_rect[1] + (ff_rect[3] - ff_text.get_height()) // 2,
                        ),
                    )
                else:
                    out_x = lut_rect[0] + lut_rect[2]
                    out_y = lut_rect[1] + lut_rect[3] // 2
                wire_color = (180, 220, 120) if display_val == 1 else (110, 110, 120)
                _draw_alpha_line(surface, (out_x, out_y), (tx, ty), wire_color, 130)
                _draw_alpha_circle(surface, (tx, ty), 2, wire_color, 160)

        _draw_lut_table(surface, lut_rect, font, lut_inputs, active_idx, table)

    # Output pins are drawn via OMUX routing above.


def draw_io_pads(
    surface,
    origin: tuple[int, int],
    cell: int,
    grid_w: int,
    grid_h: int,
    io: dict,
    font,
) -> None:
    import pygame

    if not io:
        return
    pads = []
    pads += [(entry, "in") for entry in io.get("in", [])]
    pads += [(entry, "out") for entry in io.get("out", [])]
    pad_color = (90, 96, 106)
    in_color = (120, 160, 210)
    out_color = (180, 140, 120)
    lattice_w, lattice_h = lattice_dims(grid_w, grid_h)
    fabric_w = lattice_w * cell
    fabric_h = lattice_h * cell
    x0, y0 = origin
    edge_color = (90, 96, 106)
    for entry, kind in pads:
        x = int(entry.get("x", 0))
        y = int(entry.get("y", 0))
        side = entry.get("side", "w")
        name = entry.get("name", "")
        col = 2 * x + 1
        row = 2 * y + 1
        cx, cy = node_center(origin, cell, col, row)
        offset = cell // 2 + 8
        if side == "w":
            px, py = x0 - offset, cy
            edge_pt = (x0, cy)
        elif side == "e":
            px, py = x0 + fabric_w + offset, cy
            edge_pt = (x0 + fabric_w, cy)
        elif side == "n":
            px, py = cx, y0 - offset
            edge_pt = (cx, y0)
        else:
            px, py = cx, y0 + fabric_h + offset
            edge_pt = (cx, y0 + fabric_h)
        pygame.draw.line(surface, edge_color, (px, py), edge_pt, 1)
        rect = (px - 4, py - 4, 8, 8)
        pygame.draw.rect(surface, pad_color, rect, 1)
        color = in_color if kind == "in" else out_color
        pygame.draw.rect(surface, color, (rect[0] + 1, rect[1] + 1, rect[2] - 2, rect[3] - 2))
        if name and font:
            label = font.render(name, True, color)
            surface.blit(label, (px + 6, py - label.get_height() // 2))


def _draw_lut_table(
    surface,
    rect: tuple[int, int, int, int],
    font,
    lut_inputs: int,
    active_row: int | None = None,
    table: list[int] | None = None,
) -> None:
    import pygame

    x, y, w, h = rect
    rows = 2 ** lut_inputs
    cols = lut_inputs + 1  # inputs + output
    lut_header_h = 12
    col_header_h = 12
    table_x = x
    table_w = w
    table_y = y + lut_header_h + col_header_h + 3
    table_h = h - lut_header_h - col_header_h - 3
    if rows <= 0 or table_h <= 4:
        return

    row_h = table_h / rows
    col_w = table_w / cols
    if row_h < 6 or col_w < 6:
        return

    grid_color = (80, 86, 96)
    for r in range(rows + 1):
        yy = int(table_y + r * row_h)
        pygame.draw.line(surface, grid_color, (table_x, yy), (table_x + table_w, yy), 1)
    for c in range(cols + 1):
        xx = int(table_x + c * col_w)
        pygame.draw.line(surface, grid_color, (xx, table_y), (xx, table_y + table_h), 1)

    # Column header labels
    for c in range(lut_inputs):
        label = font.render(f"I{c}", True, (150, 150, 160))
        surface.blit(label, (int(table_x + c * col_w + 3), y + lut_header_h + 2))
    out_label = font.render("O", True, (150, 150, 160))
    surface.blit(out_label, (int(table_x + lut_inputs * col_w + 3), y + lut_header_h + 2))

    # Truth table contents (default zeros)
    for r in range(rows):
        bits = format(r, f"0{lut_inputs}b")
        if active_row is not None and r == active_row:
            pygame.draw.rect(
                surface,
                (70, 86, 110),
                (table_x, int(table_y + r * row_h), table_w, int(row_h) + 1),
                0,
            )
        for c in range(lut_inputs):
            val = font.render(bits[c], True, (140, 140, 150))
            vx = int(table_x + c * col_w + col_w / 2 - val.get_width() / 2)
            vy = int(table_y + r * row_h + row_h / 2 - val.get_height() / 2)
            surface.blit(val, (vx, vy))
        out_val = "0"
        if table is not None and r < len(table):
            out_val = str(table[r])
        out = font.render(out_val, True, (140, 140, 150))
        ox = int(table_x + lut_inputs * col_w + col_w / 2 - out.get_width() / 2)
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
    offsets_h: list[int],
    offsets_v: list[int],
    color: tuple[int, int, int],
) -> None:
    import pygame

    cx, cy = center
    half = size // 2
    tracks = min(len(offsets_h), len(offsets_v))
    for idx in range(tracks):
        nxt = (idx + 1) % tracks
        prv = (idx - 1) % tracks
        north = (cx + offsets_h[idx], cy - half)
        south = (cx + offsets_h[idx], cy + half)
        east = (cx + half, cy + offsets_v[idx])
        west = (cx - half, cy + offsets_v[idx])
        ne = (cx + half, cy + offsets_v[nxt])
        es = (cx + offsets_h[nxt], cy + half)
        sw = (cx - half, cy + offsets_v[prv])
        wn = (cx + offsets_h[prv], cy - half)
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
    offsets_h: list[int],
    offsets_v: list[int],
    color: tuple[int, int, int],
) -> None:
    import pygame

    cx, cy = center
    half = size // 2
    cell_half = cell // 2
    if side in ("w", "e"):
        for off in offsets_v:
            x = cx + off
            pygame.draw.line(surface, color, (x, cy - cell_half), (x, cy - half), 1)
            pygame.draw.line(surface, color, (x, cy - half), (x, cy + half), 1)
            pygame.draw.line(surface, color, (x, cy + half), (x, cy + cell_half), 1)
    else:
        for off in offsets_h:
            y = cy + off
            pygame.draw.line(surface, color, (cx - cell_half, y), (cx - half, y), 1)
            pygame.draw.line(surface, color, (cx - half, y), (cx + half, y), 1)
            pygame.draw.line(surface, color, (cx + half, y), (cx + cell_half, y), 1)


def _offsets_for_side(side: Side, offsets_h: list[int], offsets_v: list[int]) -> list[int]:
    return offsets_h if side in ("n", "s") else offsets_v


def _lane_label(idx: int, orientation: str, track_dirs: dict[str, int] | None, routing_dir: str) -> str:
    if routing_dir != "uni":
        return f"T{idx}"
    dirs = track_dirs or {}
    if orientation == "h":
        e_count = int(dirs.get("e", 0))
        if idx < e_count:
            return f"E{idx}"
        return f"W{idx - e_count}"
    n_count = int(dirs.get("n", 0))
    if idx < n_count:
        return f"N{idx}"
    return f"S{idx - n_count}"
