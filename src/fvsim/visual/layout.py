from __future__ import annotations

TRACKS = 4
TRACK_SPAN_RATIO = 0.45
CLB_SIZE_RATIO = 0.7


def lattice_dims(grid_w: int, grid_h: int) -> tuple[int, int]:
    return grid_w * 2 + 1, grid_h * 2 + 1


def cell_size(area_w: int, area_h: int, grid_w: int, grid_h: int) -> int:
    lattice_w, lattice_h = lattice_dims(grid_w, grid_h)
    cell_w = area_w // lattice_w
    cell_h = area_h // lattice_h
    return max(14, min(cell_w, cell_h))


def origin(
    fabric_rect: tuple[int, int, int, int], cell: int, grid_w: int, grid_h: int
) -> tuple[int, int]:
    lattice_w, lattice_h = lattice_dims(grid_w, grid_h)
    total_w = lattice_w * cell
    total_h = lattice_h * cell
    x0 = fabric_rect[0] + max(0, (fabric_rect[2] - total_w) // 2)
    y0 = fabric_rect[1] + max(0, (fabric_rect[3] - total_h) // 2)
    return x0, y0


def node_center(origin_xy: tuple[int, int], cell: int, col: int, row: int) -> tuple[int, int]:
    x0, y0 = origin_xy
    return x0 + col * cell + cell // 2, y0 + row * cell + cell // 2


def track_span(cell: int) -> int:
    return int(cell * TRACK_SPAN_RATIO)


def track_offsets(
    cell: int,
    tracks: int = TRACKS,
    track_dirs: dict[str, int] | None = None,
    orientation: str = "h",
    routing_dir: str = "bi",
) -> list[int]:
    span = track_span(cell)
    if routing_dir != "uni":
        return _even_offsets(tracks, span)
    dirs = track_dirs or {}
    if orientation == "h":
        e_count = int(dirs.get("e", tracks // 2))
        w_count = int(dirs.get("w", tracks - e_count))
        return _split_offsets(e_count, w_count, span)
    n_count = int(dirs.get("n", tracks // 2))
    s_count = int(dirs.get("s", tracks - n_count))
    return _split_offsets(n_count, s_count, span)


def _even_offsets(count: int, span: int) -> list[int]:
    if count <= 1:
        return [0]
    start = -span // 2
    step = span / max(1, count - 1)
    return [int(start + idx * step) for idx in range(count)]


def _split_offsets(neg_count: int, pos_count: int, span: int) -> list[int]:
    half = max(1, span // 2)
    neg = _group_offsets(neg_count, -half, -1)
    pos = _group_offsets(pos_count, 1, half)
    return neg + pos


def _group_offsets(count: int, start: int, end: int) -> list[int]:
    if count <= 0:
        return []
    if count == 1:
        return [int((start + end) / 2)]
    step = (end - start) / (count - 1)
    return [int(round(start + idx * step)) for idx in range(count)]


def clb_size(cell: int) -> int:
    return int(cell * CLB_SIZE_RATIO)


def sb_size(cell: int) -> int:
    return int(cell * CLB_SIZE_RATIO)


def cb_size(cell: int) -> int:
    return int(cell * CLB_SIZE_RATIO)
