from __future__ import annotations

from .layout import lattice_dims, node_center, sb_size, track_offsets
from .draw_util import _net_color, _offsets_for_side

Side = str
Connection = tuple[Side, int, Side, int] | tuple[Side, int, Side, int, str]


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
    connections_for=None,
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
