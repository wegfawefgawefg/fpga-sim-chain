from __future__ import annotations

from dataclasses import dataclass

from .load import Block, Design
from .logic import and2, not1, or2, xor2


Value = str


@dataclass
class TickResult:
    tick: int
    nets: dict[str, Value]


def simulate(
    design: Design,
    inputs: dict[str, Value] | list[dict[str, Value]],
    ticks: int,
) -> list[TickResult]:
    values = {net: "X" for net in design.nets}
    results: list[TickResult] = []
    blocks = [design.blocks[name] for name in sorted(design.blocks.keys())]
    inputs_by_tick = _normalize_inputs(inputs, ticks)

    for tick in range(ticks):
        _apply_inputs(values, design, inputs_by_tick[tick])
        values = _eval_combinational(values, design, blocks)
        values = _eval_sequential(values, design, blocks)
        results.append(TickResult(tick=tick, nets=dict(values)))
    return results


def _normalize_inputs(
    inputs: dict[str, Value] | list[dict[str, Value]],
    ticks: int,
) -> list[dict[str, Value]]:
    if isinstance(inputs, dict):
        return [inputs for _ in range(ticks)]
    if ticks <= 0:
        ticks = len(inputs)
    if ticks != len(inputs):
        raise ValueError("ticks must match input sequence length")
    return list(inputs)


def _apply_inputs(values: dict[str, Value], design: Design, inputs: dict[str, Value]) -> None:
    for port, direction in design.ports.items():
        if direction != "in":
            continue
        if port not in inputs:
            continue
        net = design.port_nets.get(port, port)
        values[net] = inputs[port]


def _eval_combinational(
    values: dict[str, Value],
    design: Design,
    blocks: list[Block],
) -> dict[str, Value]:
    current = dict(values)
    max_iters = max(1, len(blocks))

    for _ in range(max_iters):
        updated = dict(current)
        for block in blocks:
            if block.mode in {"and2", "or2", "xor2", "not"}:
                out_net, out_val = _eval_gate(block, design, current)
                updated[out_net] = out_val
        if updated == current:
            break
        current = updated

    return current


def _eval_gate(block: Block, design: Design, values: dict[str, Value]) -> tuple[str, Value]:
    pin = block.name
    if block.mode == "not":
        in_net = _resolve_pin_net(design, pin, "a", _fallback_input(block, 0))
        out_net = _resolve_pin_net(design, pin, "y", None)
        return out_net, not1(values.get(in_net, "X"))

    a_net = _resolve_pin_net(design, pin, "a", _fallback_input(block, 0))
    b_net = _resolve_pin_net(design, pin, "b", _fallback_input(block, 1))
    out_net = _resolve_pin_net(design, pin, "y", None)
    a = values.get(a_net, "X")
    b = values.get(b_net, "X")

    if block.mode == "and2":
        return out_net, and2(a, b)
    if block.mode == "or2":
        return out_net, or2(a, b)
    if block.mode == "xor2":
        return out_net, xor2(a, b)
    raise ValueError(f"Unknown combinational mode: {block.mode}")


def _eval_sequential(values: dict[str, Value], design: Design, blocks: list[Block]) -> dict[str, Value]:
    updated = dict(values)
    for block in blocks:
        if block.mode != "dff":
            continue
        d_net = _resolve_pin_net(design, block.name, "d", _fallback_ff(block, "d"))
        q_net = _resolve_pin_net(design, block.name, "q", _fallback_ff(block, "q"))
        rst_net = _resolve_optional_pin(design, block.name, "rst", _fallback_ff(block, "rst"))
        rst_val = values.get(rst_net, "0") if rst_net else "0"
        if rst_val == "1":
            updated[q_net] = "0"
        elif rst_val == "X":
            updated[q_net] = "X"
        else:
            updated[q_net] = values.get(d_net, "X")
    return updated


def _resolve_pin_net(design: Design, block: str, pin: str, fallback: str | None) -> str:
    key = f"{block}.{pin}"
    mapped = design.pin_nets.get(key)
    if mapped and fallback and mapped != fallback:
        raise ValueError(f"Pin mapping mismatch for {key}: {mapped} vs {fallback}")
    if mapped:
        return mapped
    if fallback:
        return fallback
    raise ValueError(f"Missing net mapping for {key}")


def _resolve_optional_pin(
    design: Design, block: str, pin: str, fallback: str | None
) -> str | None:
    key = f"{block}.{pin}"
    mapped = design.pin_nets.get(key)
    if mapped and fallback and mapped != fallback:
        raise ValueError(f"Pin mapping mismatch for {key}: {mapped} vs {fallback}")
    if mapped:
        return mapped
    return fallback


def _fallback_input(block: Block, index: int) -> str | None:
    if index < len(block.inputs):
        return block.inputs[index]
    return None


def _fallback_ff(block: Block, pin: str) -> str | None:
    if block.ff is None:
        return None
    return block.ff.get(pin)
