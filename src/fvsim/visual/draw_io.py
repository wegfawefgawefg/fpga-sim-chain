from __future__ import annotations

from .layout import lattice_dims, node_center


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
