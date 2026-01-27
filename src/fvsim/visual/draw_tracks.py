from __future__ import annotations

from .layout import lattice_dims, node_center, sb_size, track_offsets


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
