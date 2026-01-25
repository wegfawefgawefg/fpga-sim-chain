from __future__ import annotations

from pathlib import Path
import os
import time

from .draw import (
    Connection,
    draw_clbs,
    draw_connection_boxes,
    draw_route_polyline,
    draw_switch_boxes,
    draw_tracks,
)
from .layout import cell_size, origin
from .routes import RoutingData, Route, load_routing, route_points, segment_points, switch_point, tap_point


def run_visual(
    bit_path: Path | None,
    grid: str = "4x4",
    demo: bool = False,
    headless: bool = False,
    runtime: float = 0.0,
) -> None:
    try:
        import pygame
    except Exception as exc:  # pragma: no cover - optional
        raise SystemExit(f"pygame required for visual mode: {exc}")

    if headless:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

    routing = load_routing(bit_path) if bit_path and not demo else RoutingData([], [], [], [], {})
    grid_w, grid_h = _parse_grid(grid)
    if routing.fabric.get("w"):
        grid_w = routing.fabric.get("w")
    if routing.fabric.get("h"):
        grid_h = routing.fabric.get("h")

    window_w = 1280
    window_h = 720
    fabric_rect = _compute_fabric_rect(window_w, window_h)
    base_cell = cell_size(fabric_rect[2], fabric_rect[3], grid_w, grid_h)
    base_origin = origin(fabric_rect, base_cell, grid_w, grid_h)
    zoom = 1.0
    pan_x = 0.0
    pan_y = 0.0

    pygame.init()
    window = pygame.display.set_mode((window_w, window_h))
    surface = pygame.Surface((window_w, window_h))
    pygame.display.set_caption("fvsim visual")
    font = pygame.font.SysFont("monospace", 12)
    label_font = pygame.font.SysFont("monospace", 10)

    show_clb_labels = True
    show_cb_labels = True
    show_sb_labels = True
    show_lane_labels = True
    show_clb_internals = True
    running = True
    start_time = time.time()
    dragging = False
    last_mouse = (0, 0)
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (
                event.type == pygame.KEYDOWN
                and (event.key == pygame.K_ESCAPE or event.key == pygame.K_q)
            ):
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1:
                    show_clb_labels = not show_clb_labels
                if event.key == pygame.K_2:
                    show_cb_labels = not show_cb_labels
                if event.key == pygame.K_3:
                    show_sb_labels = not show_sb_labels
                if event.key == pygame.K_4:
                    show_lane_labels = not show_lane_labels
                if event.key == pygame.K_5:
                    show_clb_internals = not show_clb_internals
            if event.type == pygame.MOUSEWHEEL:
                zoom, pan_x, pan_y = _handle_zoom(
                    zoom,
                    pan_x,
                    pan_y,
                    base_origin,
                    event.y,
                    pygame.mouse.get_pos(),
                )
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                dragging = True
                last_mouse = event.pos
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                dragging = False
            if event.type == pygame.MOUSEMOTION and dragging:
                dx = event.pos[0] - last_mouse[0]
                dy = event.pos[1] - last_mouse[1]
                pan_x += dx
                pan_y += dy
                last_mouse = event.pos

        keys = pygame.key.get_pressed()
        pan_x, pan_y = _handle_pan(keys, pan_x, pan_y)

        cell = max(8, int(base_cell * zoom))
        origin_xy = (int(base_origin[0] + pan_x), int(base_origin[1] + pan_y))

        surface.fill((18, 18, 20))
        _draw_grid(surface, origin_xy, cell, grid_w, grid_h)
        draw_tracks(surface, origin_xy, cell, grid_w, grid_h, label_font, show_lane_labels)
        draw_switch_boxes(
            surface,
            origin_xy,
            cell,
            grid_w,
            grid_h,
            label_font,
            show_sb_labels,
            connections_for=_demo_sb_connections,
        )
        pins_per_side = routing.fabric.get("pins_per_side", 4)
        slices_per_clb = routing.fabric.get("slices_per_clb", 4)
        lut_k = routing.fabric.get("lut_k", 4)
        draw_connection_boxes(
            surface,
            origin_xy,
            cell,
            grid_w,
            grid_h,
            label_font,
            pins_per_side,
            show_cb_labels,
            taps_for=_demo_cb_taps,
        )
        # Routing overlays disabled while we refine connection rendering.
        draw_clbs(
            surface,
            origin_xy,
            cell,
            grid_w,
            grid_h,
            font,
            pins_per_side,
            show_clb_labels,
            show_clb_internals,
            slices_per_clb,
            lut_k,
        )

        if runtime and (time.time() - start_time) >= runtime:
            running = False
        window.blit(surface, (0, 0))
        pygame.display.update()

    pygame.quit()


def _draw_routes(
    surface,
    routing: RoutingData,
    origin_xy: tuple[int, int],
    cell: int,
    grid_w: int,
    grid_h: int,
) -> None:
    for segment in routing.segments:
        seg = segment_points(segment, origin_xy, cell)
        if seg:
            draw_route_polyline(surface, list(seg), _net_color(segment.net))
    for sw in routing.switches:
        pt = switch_point(sw.sb, origin_xy, cell)
        if pt:
            _draw_switch_marker(surface, pt, _net_color(sw.net))
    for tap in routing.taps:
        pt = tap_point(tap, origin_xy, cell)
        if pt:
            _draw_tap_marker(surface, pt, _net_color(tap.net))


def _draw_demo(surface, origin_xy: tuple[int, int], cell: int, grid_w: int, grid_h: int) -> None:
    demo = [
        Route("net1", ["x0y0.a", "x3y0.y"]),
        Route("net2", ["x0y3.a", "x3y3.y"]),
        Route("net3", ["x0y0.a", "x0y3.y"]),
    ]
    for route in demo:
        points = route_points(route, origin_xy, cell, grid_w, grid_h)
        if len(points) >= 2:
            draw_route_polyline(surface, points, _net_color(route.net))


def _draw_switch_marker(surface, pt: tuple[int, int], color: tuple[int, int, int]) -> None:
    import pygame

    pygame.draw.circle(surface, color, pt, 3)


def _draw_tap_marker(surface, pt: tuple[int, int], color: tuple[int, int, int]) -> None:
    import pygame

    pygame.draw.rect(surface, color, (pt[0] - 2, pt[1] - 2, 4, 4))


def _demo_sb_connections(col: int, row: int) -> list[Connection]:
    key = (col + row) % 6
    if key == 0:
        return [("n", 0, "e", 1), ("w", 2, "s", 3), ("n", 1, "s", 1)]
    if key == 1:
        return [("n", 2, "s", 2), ("w", 0, "e", 0)]
    if key == 2:
        return [("n", 3, "e", 3), ("n", 3, "s", 3)]
    if key == 3:
        return [("w", 1, "e", 2), ("w", 1, "n", 1)]
    if key == 4:
        return [("s", 0, "e", 0), ("s", 0, "w", 0), ("n", 1, "w", 1)]
    return [("n", 2, "w", 1), ("s", 1, "e", 2)]


def _demo_cb_taps(col: int, row: int, side: str) -> list[tuple[str, int, int]]:
    if (col + row) % 3 == 0:
        return [(side, 0, 0), (side, 2, 1)]
    if (col + row) % 3 == 1:
        return [(side, 1, 2)]
    return [(side, 3, 3)]


def _net_color(net: str) -> tuple[int, int, int]:
    palette = [
        (235, 176, 93),
        (120, 200, 220),
        (180, 220, 120),
        (220, 140, 200),
        (210, 210, 120),
    ]
    idx = sum(ord(ch) for ch in net) % len(palette)
    return palette[idx]


def _compute_fabric_rect(window_w: int, window_h: int) -> tuple[int, int, int, int]:
    left = int(window_w * 0.06)
    top = int(window_h * 0.08)
    width = int(window_w * 0.68)
    height = int(window_h * 0.84)
    return (left, top, width, height)


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


def _draw_grid(
    surface, origin_xy: tuple[int, int], cell: int, grid_w: int, grid_h: int
) -> None:
    import pygame

    x0, y0 = origin_xy
    lattice_w = grid_w * 2 + 1
    lattice_h = grid_h * 2 + 1
    grid_color = (32, 34, 38)
    for col in range(lattice_w + 1):
        x = x0 + col * cell
        pygame.draw.line(surface, grid_color, (x, y0), (x, y0 + lattice_h * cell), 1)
    for row in range(lattice_h + 1):
        y = y0 + row * cell
        pygame.draw.line(surface, grid_color, (x0, y), (x0 + lattice_w * cell, y), 1)


def _handle_pan(keys, pan_x: float, pan_y: float) -> tuple[float, float]:
    import pygame

    speed = 4
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
    zoom_step = 0.18
    new_zoom = zoom + (zoom_step * wheel_delta)
    new_zoom = max(0.2, min(20.0, new_zoom))
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
