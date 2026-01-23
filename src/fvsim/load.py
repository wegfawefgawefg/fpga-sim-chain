from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Block:
    name: str
    mode: str
    inputs: list[str]
    ff: dict | None


@dataclass
class Design:
    top: str
    nets: list[str]
    ports: dict[str, str]
    blocks: dict[str, Block]
    pin_nets: dict[str, str]
    port_nets: dict[str, str]


def load_design(net_path: Path, bit_path: Path) -> Design:
    fnet = json.loads(net_path.read_text())
    fbit = json.loads(bit_path.read_text())

    top = fnet.get("top")
    modules = fnet.get("modules", {})
    if top not in modules:
        raise ValueError("Top module missing from netlist")
    mod = modules[top]
    nets = list(mod.get("nets", []))
    ports = {name: data["dir"] for name, data in mod.get("ports", {}).items()}

    blocks: dict[str, Block] = {}
    for name, data in fbit.get("blocks", {}).items():
        mode = data.get("mode")
        inputs = list(data.get("inputs", []))
        ff = data.get("ff")
        blocks[name] = Block(name=name, mode=mode, inputs=inputs, ff=ff)

    pin_nets: dict[str, str] = {}
    port_nets: dict[str, str] = {}
    for route in fbit.get("routes", []):
        net = route.get("net")
        if net not in nets:
            raise ValueError(f"Route references unknown net: {net}")
        for waypoint in route.get("path", []):
            if waypoint.startswith("in:"):
                port = waypoint.split(":", 1)[1]
                _record_mapping(port_nets, port, net, "port")
            elif waypoint.startswith("out:"):
                port = waypoint.split(":", 1)[1]
                _record_mapping(port_nets, port, net, "port")
            elif "." in waypoint:
                _record_mapping(pin_nets, waypoint, net, "pin")

    return Design(
        top=top,
        nets=nets,
        ports=ports,
        blocks=blocks,
        pin_nets=pin_nets,
        port_nets=port_nets,
    )


def _record_mapping(mapping: dict[str, str], key: str, value: str, label: str) -> None:
    if key in mapping and mapping[key] != value:
        raise ValueError(f"Conflicting {label} mapping for {key}")
    mapping[key] = value

