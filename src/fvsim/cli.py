from __future__ import annotations

import argparse
from pathlib import Path

from .load import load_design
from .sim import simulate


def main() -> None:
    parser = argparse.ArgumentParser(prog="fvsim")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run_parser = sub.add_parser("run", help="Run a non-visual simulation")
    run_parser.add_argument("--net", required=True, help="Input .fnet.json")
    run_parser.add_argument("--bit", required=True, help="Input .fbit.json")
    run_parser.add_argument(
        "--ticks",
        type=int,
        default=1,
        help="Number of ticks to simulate (each tick is a rising edge for dff)",
    )
    run_parser.add_argument(
        "--inputs",
        default="",
        help="Comma-separated inputs (e.g., a=0,b=1). Values: 0,1,X",
    )

    args = parser.parse_args()

    if args.cmd == "run":
        design = load_design(Path(args.net), Path(args.bit))
        inputs = _parse_inputs(args.inputs)
        results = simulate(design, inputs, ticks=args.ticks)
        _print_results(design.nets, results)


def _parse_inputs(raw: str) -> dict[str, str]:
    inputs: dict[str, str] = {}
    if not raw:
        return inputs
    for pair in raw.split(","):
        if not pair:
            continue
        if "=" not in pair:
            raise ValueError("Inputs must be in name=value form")
        name, value = pair.split("=", 1)
        name = name.strip()
        value = value.strip().upper()
        if value not in {"0", "1", "X"}:
            raise ValueError(f"Invalid input value for {name}: {value}")
        inputs[name] = value
    return inputs


def _print_results(nets: list[str], results: list) -> None:
    for result in results:
        parts = [f"{net}={result.nets.get(net, 'X')}" for net in nets]
        print(f"tick {result.tick}: " + " ".join(parts))


if __name__ == "__main__":
    main()
