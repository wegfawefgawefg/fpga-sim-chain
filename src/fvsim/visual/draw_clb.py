from __future__ import annotations

from .layout import clb_size
from .draw_util import (
    _draw_alpha_circle,
    _draw_alpha_line,
    _pin_offsets_for_side,
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
    clb_cells: dict | None = None,
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
                    clb_cells,
                )


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
    clb_cells: dict | None,
) -> None:
    import math
    import pygame

    x, y, w, h = rect
    pad = max(2, w // 30)
    inner = (x + pad, y + pad, w - pad * 2, h - pad * 2)
    slice_count = max(1, slices_per_clb)
    cols = max(1, int(math.ceil(math.sqrt(slice_count))))
    rows = max(1, int(math.ceil(slice_count / cols)))
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

    clb_slices = None
    if clb_cells:
        clb_cell = clb_cells.get((clb_xy[0], clb_xy[1]))
        if clb_cell:
            clb_slices = clb_cell.slices
    if clb_slices:
        slice_outputs = [None] * slice_count
        slice_inputs = [[] for _ in range(slice_count)]
        slice_tables = [None] * slice_count
        for entry in clb_slices:
            sidx = int(entry.index)
            if sidx < 0 or sidx >= slice_count:
                continue
            slice_outputs[sidx] = (
                entry.output.side,
                int(entry.output.pin),
                bool(entry.output.use_ff),
            )
            slice_inputs[sidx] = entry.inputs
            slice_tables[sidx] = entry.table
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
    cols = lut_inputs + 1
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

    for c in range(lut_inputs):
        label = font.render(f"I{c}", True, (150, 150, 160))
        surface.blit(label, (int(table_x + c * col_w + 3), y + lut_header_h + 2))
    out_label = font.render("O", True, (150, 150, 160))
    surface.blit(out_label, (int(table_x + lut_inputs * col_w + 3), y + lut_header_h + 2))

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
