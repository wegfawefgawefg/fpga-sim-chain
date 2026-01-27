from __future__ import annotations

from typing import Callable

from .layout import cb_size, clb_size, node_center, track_offsets
from .draw_util import _draw_x, _net_color, _offsets_for_side, _pin_offsets_for_side

Side = str
Tap = tuple[Side, int, int] | tuple[Side, int, int, str]


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
                        taps_for(x, y, side),
                        (cx, cy),
                        side,
                        pins_per_side,
                        offsets_h,
                        offsets_v,
                    )


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


def _cb_side(col: int, row: int, cb_col: int, cb_row: int) -> Side:
    if cb_col < col:
        return "w"
    if cb_col > col:
        return "e"
    if cb_row < row:
        return "n"
    return "s"


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
