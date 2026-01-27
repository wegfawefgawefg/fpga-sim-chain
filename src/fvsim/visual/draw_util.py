from __future__ import annotations


def draw_route_polyline(surface, points: list[tuple[int, int]], color: tuple[int, int, int]) -> None:
    for idx in range(len(points) - 1):
        _draw_manhattan(surface, points[idx], points[idx + 1], color)


def draw_route_arrow(
    surface,
    start: tuple[int, int],
    end: tuple[int, int],
    flow: str | None,
    color: tuple[int, int, int],
) -> None:
    import math
    import pygame

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


def _draw_x(surface, center: tuple[int, int], color: tuple[int, int, int]) -> None:
    import pygame

    cx, cy = center
    pygame.draw.line(surface, color, (cx - 2, cy - 2), (cx + 2, cy + 2), 1)
    pygame.draw.line(surface, color, (cx - 2, cy + 2), (cx + 2, cy - 2), 1)


def _pin_offsets_for_side(size: int, pins_per_side: int, side: str) -> list[int]:
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


def _offsets_for_side(side: str, offsets_h: list[int], offsets_v: list[int]) -> list[int]:
    return offsets_h if side in ("n", "s") else offsets_v


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
