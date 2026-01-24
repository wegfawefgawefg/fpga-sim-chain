from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json


@dataclass
class Fabric:
    width: int
    height: int
    blocks: dict[str, dict]


@dataclass
class Route:
    net: str
    path: list[str]


TRACKS = 4
TRACK_SPAN_RATIO = 0.45


def load_fabric(bit_path: Path) -> Fabric:
    data = json.loads(bit_path.read_text())
    fabric = data.get("fabric", {})
    width = int(fabric.get("w", 0))
    height = int(fabric.get("h", 0))
    if width <= 0 or height <= 0:
        raise ValueError("fabric.w and fabric.h must be positive")
    return Fabric(width=width, height=height, blocks=data.get("blocks", {}))


def load_routes(bit_path: Path) -> list[Route]:
    data = json.loads(bit_path.read_text())
    routes = []
    for route in data.get("routes", []):
        routes.append(Route(net=route.get("net", ""), path=list(route.get("path", []))))
    return routes


def run_visual(bit_path: Path | None, grid: str = "4x4", demo: bool = False) -> None:
    try:
        import pygame
    except Exception as exc:  # pragma: no cover - optional
        raise SystemExit(f"pygame required for visual mode: {exc}")

    routes = load_routes(bit_path) if bit_path and not demo else []
    grid_w, grid_h = _parse_grid(grid)

    window_w = 1280
    window_h = 720
    fabric_rect = _compute_fabric_rect(window_w, window_h)
    base_cell = _compute_cell_size(fabric_rect[2], fabric_rect[3], grid_w, grid_h)
    base_origin = _compute_origin(fabric_rect, base_cell, grid_w, grid_h)
    zoom = 1.0
    pan_x = 0.0
    pan_y = 0.0

    pygame.init()
    window = pygame.display.set_mode((window_w, window_h))
    surface = pygame.Surface((window_w, window_h))
    pygame.display.set_caption("fvsim visual")
    font = pygame.font.SysFont("monospace", 12)
    label_font = pygame.font.SysFont("monospace", 10)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (
                event.type == pygame.KEYDOWN
                and (event.key == pygame.K_ESCAPE or event.key == pygame.K_q)
            ):
                running = False
            if event.type == pygame.MOUSEWHEEL:
                zoom, pan_x, pan_y = _handle_zoom(
                    zoom,
                    pan_x,
                    pan_y,
                    base_origin,
                    event.y,
                    pygame.mouse.get_pos(),
                )

        keys = pygame.key.get_pressed()
        pan_x, pan_y = _handle_pan(keys, pan_x, pan_y)

        cell = max(8, int(base_cell * zoom))
        origin = (int(base_origin[0] + pan_x), int(base_origin[1] + pan_y))

        surface.fill((18, 18, 20))
        # Outline disabled while panning/zooming to reduce visual clutter.
        _draw_tracks(surface, origin, cell, grid_w, grid_h)
        _draw_switch_boxes(surface, origin, cell, grid_w, grid_h, label_font)
        if demo:
            _draw_demo_routes(surface, origin, cell, grid_w, grid_h)
        else:
            _draw_routes_from_bit(surface, routes, origin, cell, grid_w, grid_h)
        _draw_connection_boxes(surface, origin, cell, grid_w, grid_h, label_font)
        _draw_clbs(surface, origin, cell, grid_w, grid_h, font)

        window.blit(surface, (0, 0))
        pygame.display.update()

    pygame.quit()


def _compute_fabric_rect(window_w: int, window_h: int) -> tuple[int, int, int, int]:
    left = int(window_w * 0.06)
    top = int(window_h * 0.08)
    width = int(window_w * 0.68)
    height = int(window_h * 0.84)
    return (left, top, width, height)


def _compute_cell_size(area_w: int, area_h: int, grid_w: int, grid_h: int) -> int:
    lattice_w = grid_w * 2 + 1
    lattice_h = grid_h * 2 + 1
    cell_w = area_w // lattice_w
    cell_h = area_h // lattice_h
    return max(14, min(cell_w, cell_h))


def _compute_origin(
    fabric_rect: tuple[int, int, int, int], cell: int, grid_w: int, grid_h: int
) -> tuple[int, int]:
    lattice_w = grid_w * 2 + 1
    lattice_h = grid_h * 2 + 1
    total_w = lattice_w * cell
    total_h = lattice_h * cell
    x0 = fabric_rect[0] + max(0, (fabric_rect[2] - total_w) // 2)
    y0 = fabric_rect[1] + max(0, (fabric_rect[3] - total_h) // 2)
    return x0, y0


def _draw_fabric_outline(surface, rect: tuple[int, int, int, int]) -> None:
    import pygame

    pygame.draw.rect(surface, (28, 28, 32), rect)
    pygame.draw.rect(surface, (80, 86, 96), rect, 2)


def _draw_tracks(
    surface,
    origin: tuple[int, int],
    cell: int,
    grid_w: int,
    grid_h: int,
) -> None:
    import pygame

    x0, y0 = origin
    lattice_w = grid_w * 2 + 1
    lattice_h = grid_h * 2 + 1
    line_color = (62, 66, 72)
    span = _track_span(cell)
    for row in range(0, lattice_h, 2):
        y_center = y0 + row * cell + cell // 2
        for t in range(TRACKS):
            y = y_center + _track_offset(span, t)
            pygame.draw.line(
                surface, line_color, (x0, y), (x0 + lattice_w * cell, y), 1
            )
    for col in range(0, lattice_w, 2):
        x_center = x0 + col * cell + cell // 2
        for t in range(TRACKS):
            x = x_center + _track_offset(span, t)
            pygame.draw.line(
                surface, line_color, (x, y0), (x, y0 + lattice_h * cell), 1
            )


def _track_span(cell: int) -> int:
    return int(cell * TRACK_SPAN_RATIO)


def _track_offset(span: int, track: int) -> int:
    start = -span // 2
    step = span / max(1, TRACKS - 1)
    return int(start + track * step)


def _draw_switch_boxes(
    surface,
    origin: tuple[int, int],
    cell: int,
    grid_w: int,
    grid_h: int,
    font,
) -> None:
    import pygame

    x0, y0 = origin
    lattice_w = grid_w * 2 + 1
    lattice_h = grid_h * 2 + 1
    span = _track_span(cell)
    size = int(cell * 0.7)
    color = (90, 96, 106)
    for row in range(0, lattice_h, 2):
        for col in range(0, lattice_w, 2):
            cx = x0 + col * cell + cell // 2
            cy = y0 + row * cell + cell // 2
            rect = (cx - size // 2, cy - size // 2, size, size)
            pygame.draw.rect(surface, color, rect, 1)
            pygame.draw.line(
                surface, color, (cx - size // 2, cy), (cx + size // 2, cy), 1
            )
            pygame.draw.line(
                surface, color, (cx, cy - size // 2), (cx, cy + size // 2), 1
            )
            label = font.render("SB", True, (120, 120, 130))
            surface.blit(label, (cx - size // 2 + 1, cy - size // 2 - 10))


def _draw_clbs(
    surface,
    origin: tuple[int, int],
    cell: int,
    grid_w: int,
    grid_h: int,
    font,
) -> None:
    import pygame

    x0, y0 = origin
    size = int(cell * 0.7)
    inset = (cell - size) // 2
    for y in range(grid_h):
        for x in range(grid_w):
            row = 2 * y + 1
            col = 2 * x + 1
            rect = (x0 + col * cell + inset, y0 + row * cell + inset, size, size)
            pygame.draw.rect(surface, (46, 48, 54), rect)
            pygame.draw.rect(surface, (90, 96, 106), rect, 1)
            label = font.render("CLB", True, (150, 150, 160))
            surface.blit(label, (rect[0] + 5, rect[1] + 5))


def _draw_connection_boxes(
    surface,
    origin: tuple[int, int],
    cell: int,
    grid_w: int,
    grid_h: int,
    font,
) -> None:
    import pygame

    x0, y0 = origin
    span = _track_span(cell)
    size = int(cell * 0.7)
    color = (90, 96, 106)
    for y in range(grid_h):
        for x in range(grid_w):
            row = 2 * y + 1
            col = 2 * x + 1
            cx = x0 + col * cell + cell // 2
            cy = y0 + row * cell + cell // 2
            cb_left = (x0 + (col - 1) * cell + cell // 2, cy)
            cb_right = (x0 + (col + 1) * cell + cell // 2, cy)
            cb_top = (cx, y0 + (row - 1) * cell + cell // 2)
            cb_bottom = (cx, y0 + (row + 1) * cell + cell // 2)
            for px, py in (cb_left, cb_right, cb_top, cb_bottom):
                rect = (px - size // 2, py - size // 2, size, size)
                pygame.draw.rect(surface, color, rect, 1)
                label = font.render("CB", True, (120, 120, 130))
                surface.blit(label, (rect[0] + 1, rect[1] - 10))


def _draw_routes_from_bit(
    surface,
    routes: list[Route],
    origin: tuple[int, int],
    cell: int,
    grid_w: int,
    grid_h: int,
) -> None:
    for route in routes:
        if len(route.path) < 2:
            continue
        points = []
        for idx, waypoint in enumerate(route.path):
            prev_wp = route.path[idx - 1] if idx > 0 else None
            next_wp = route.path[idx + 1] if idx + 1 < len(route.path) else None
            pt = _waypoint_to_point(
                waypoint, route.net, origin, cell, grid_w, grid_h, prev_wp, next_wp
            )
            if pt is not None:
                points.append(pt)
        if len(points) < 2:
            continue
        color = _net_color(route.net)
        for idx in range(len(points) - 1):
            _draw_manhattan(surface, points[idx], points[idx + 1], color)


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
    x0, y0 = origin
    cx = x0 + col * cell + cell // 2
    cy = y0 + row * cell + cell // 2
    span = _track_span(cell)
    if vertical:
        return (cx + _track_offset(span, track), cy)
    return (cx, cy + _track_offset(span, track))


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


def _draw_demo_routes(
    surface,
    origin: tuple[int, int],
    cell: int,
    grid_w: int,
    grid_h: int,
) -> None:
    demo_routes = [
        Route("net1", ["x0y0.a", "x3y0.y"]),
        Route("net2", ["x0y3.a", "x3y3.y"]),
        Route("net3", ["x0y0.a", "x0y3.y"]),
    ]
    _draw_routes_from_bit(surface, demo_routes, origin, cell, grid_w, grid_h)


def _track_index(net: str) -> int:
    if not net:
        return 0
    return sum(ord(ch) for ch in net) % max(1, TRACKS)


def _net_color(net: str) -> tuple[int, int, int]:
    palette = [
        (235, 176, 93),
        (120, 200, 220),
        (180, 220, 120),
        (220, 140, 200),
        (210, 210, 120),
    ]
    idx = _track_index(net) % len(palette)
    return palette[idx]


def _parse_block_coord(name: str) -> tuple[int | None, int | None]:
    if not name.startswith("x") or "y" not in name:
        return None, None
    try:
        x_str, y_str = name[1:].split("y", 1)
        return int(x_str), int(y_str)
    except ValueError:
        return None, None


def _parse_grid(value: str) -> tuple[int, int]:
    raw = value.lower().replace(" ", "")
    if "x" not in raw:
        raise ValueError("grid must look like 4x4")
    parts = raw.split("x", 1)
    try:
        w = int(parts[0])
        h = int(parts[1])
    except ValueError as exc:
        raise ValueError("grid must look like 4x4") from exc
    if w <= 0 or h <= 0:
        raise ValueError("grid must be positive")
    return w, h


def _handle_pan(keys, pan_x: float, pan_y: float) -> tuple[float, float]:
    import pygame

    speed = 2
    if keys[pygame.K_LEFT] or keys[pygame.K_a]:
        pan_x += speed
    if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
        pan_x -= speed
    if keys[pygame.K_UP] or keys[pygame.K_w]:
        pan_y += speed
    if keys[pygame.K_DOWN] or keys[pygame.K_s]:
        pan_y -= speed
    return pan_x, pan_y


def _handle_zoom(
    zoom: float,
    pan_x: float,
    pan_y: float,
    base_origin: tuple[int, int],
    wheel_delta: int,
    mouse_pos: tuple[int, int],
) -> tuple[float, float, float]:
    import pygame

    zoom_step = 0.18
    new_zoom = zoom + (zoom_step * wheel_delta)
    new_zoom = max(0.1, min(8.0, new_zoom))
    if new_zoom == zoom:
        return zoom, pan_x, pan_y

    mx, my = mouse_pos
    origin_x = base_origin[0] + pan_x
    origin_y = base_origin[1] + pan_y
    world_x = (mx - origin_x) / zoom
    world_y = (my - origin_y) / zoom
    new_origin_x = mx - world_x * new_zoom
    new_origin_y = my - world_y * new_zoom
    pan_x = new_origin_x - base_origin[0]
    pan_y = new_origin_y - base_origin[1]
    return new_zoom, pan_x, pan_y
