from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .sexpr import parse, tokenize


@dataclass
class ShdlModule:
    name: str
    ports: dict[str, str]
    wires: list[str]
    cells: dict[str, dict]


def parse_shdl(text: str) -> ShdlModule:
    exprs = parse(tokenize(text))
    if len(exprs) != 1:
        raise ValueError("Expected exactly one top-level (module ...) form")
    mod = exprs[0]
    if not isinstance(mod, list) or len(mod) < 2 or mod[0] != "module":
        raise ValueError("Top-level form must be (module <name> ...) ")
    name = _require_symbol(mod[1], "module name")
    ports: dict[str, str] = {}
    wires: list[str] = []
    cells: dict[str, dict] = {}

    for form in mod[2:]:
        if not isinstance(form, list) or not form:
            raise ValueError("Expected a list form inside module")
        head = form[0]
        if head == "ports":
            _parse_ports(form[1:], ports)
        elif head == "wire":
            _parse_wires(form[1:], wires)
        else:
            _parse_cell(form, cells)

    return ShdlModule(name=name, ports=ports, wires=wires, cells=cells)


def to_fnet(mod: ShdlModule, fabric: dict | None = None) -> dict:
    nets = set(mod.wires)
    for pname in mod.ports.keys():
        nets.add(pname)
    for cell in mod.cells.values():
        for net in cell["pins"].values():
            nets.add(net)
    fnet = {
        "top": mod.name,
        "modules": {
            mod.name: {
                "ports": {name: {"dir": direction} for name, direction in mod.ports.items()},
                "cells": mod.cells,
                "nets": sorted(nets),
            }
        },
    }
    if fabric:
        fnet["fabric"] = fabric
    return fnet


def _parse_ports(items: Iterable[object], ports: dict[str, str]) -> None:
    for item in items:
        if not isinstance(item, list) or len(item) != 2:
            raise ValueError("Port entries must be (in <name>) or (out <name>)")
        direction = _require_symbol(item[0], "port direction")
        if direction not in {"in", "out"}:
            raise ValueError("Port direction must be 'in' or 'out'")
        name = _require_symbol(item[1], "port name")
        if name in ports:
            raise ValueError(f"Duplicate port name: {name}")
        ports[name] = direction


def _parse_wires(items: Iterable[object], wires: list[str]) -> None:
    if not items:
        raise ValueError("(wire ...) must declare at least one net")
    for item in items:
        name = _require_symbol(item, "wire name")
        if name in wires:
            raise ValueError(f"Duplicate wire name: {name}")
        wires.append(name)


def _parse_cell(form: list, cells: dict[str, dict]) -> None:
    head = _require_symbol(form[0], "cell type")
    if head in {"and2", "or2", "xor2"}:
        if len(form) != 5:
            raise ValueError(f"({head} <inst> <a> <b> <y>) required")
        inst = _require_symbol(form[1], "instance name")
        _ensure_unique_cell(inst, cells)
        cells[inst] = {
            "type": head,
            "pins": {
                "a": _require_symbol(form[2], "a"),
                "b": _require_symbol(form[3], "b"),
                "y": _require_symbol(form[4], "y"),
            },
        }
        return
    if head == "not":
        if len(form) != 4:
            raise ValueError("(not <inst> <a> <y>) required")
        inst = _require_symbol(form[1], "instance name")
        _ensure_unique_cell(inst, cells)
        cells[inst] = {
            "type": head,
            "pins": {
                "a": _require_symbol(form[2], "a"),
                "y": _require_symbol(form[3], "y"),
            },
        }
        return
    if head == "dff":
        _parse_dff(form, cells)
        return
    raise ValueError(f"Unknown cell type: {head}")


def _parse_dff(form: list, cells: dict[str, dict]) -> None:
    if len(form) < 3:
        raise ValueError("(dff <inst> (d <net>) (q <net>) ...) required")
    inst = _require_symbol(form[1], "instance name")
    _ensure_unique_cell(inst, cells)
    pins: dict[str, str] = {}
    for item in form[2:]:
        if not isinstance(item, list) or len(item) != 2:
            raise ValueError("dff pin entries must be (d <net>) (q <net>) ...")
        key = _require_symbol(item[0], "dff pin")
        if key not in {"d", "q", "clk", "rst"}:
            raise ValueError(f"Invalid dff pin: {key}")
        val = _require_symbol(item[1], f"{key} net")
        if key in pins:
            raise ValueError(f"Duplicate dff pin: {key}")
        pins[key] = val
    if "d" not in pins or "q" not in pins:
        raise ValueError("dff requires d and q pins")
    if "clk" not in pins:
        pins["clk"] = "clk"
    cells[inst] = {"type": "dff", "pins": pins}


def _require_symbol(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"Expected symbol for {label}")
    return value


def _ensure_unique_cell(name: str, cells: dict[str, dict]) -> None:
    if name in cells:
        raise ValueError(f"Duplicate instance name: {name}")
