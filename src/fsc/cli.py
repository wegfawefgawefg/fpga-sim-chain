from __future__ import annotations

import argparse
from pathlib import Path

import json

from .emit import write_fbit, write_fnet
from .router import FabricSpec, build_clb_config, emit_blocks, place_cells, route_fnet
from .shdl import parse_shdl, to_fnet


def main() -> None:
    parser = argparse.ArgumentParser(prog="fsc")
    sub = parser.add_subparsers(dest="cmd", required=True)

    compile_parser = sub.add_parser("compile", help="Compile SHDL to fnet")
    compile_parser.add_argument(
        "--in", dest="src", required=True, help="Input .shdl file"
    )
    compile_parser.add_argument(
        "--out", dest="out_dir", required=True, help="Output directory"
    )
    compile_parser.add_argument(
        "--fabric",
        dest="fabric_path",
        help="Fabric spec JSON file to embed in fnet",
    )
    bit_parser = sub.add_parser("bit", help="Compile SHDL to fbit (with simple routing)")
    bit_parser.add_argument("--in", dest="src", required=True, help="Input .shdl file")
    bit_parser.add_argument("--out", dest="out_dir", required=True, help="Output directory")
    bit_parser.add_argument("--w", type=int, default=4, help="Fabric width in CLBs")
    bit_parser.add_argument("--h", type=int, default=4, help="Fabric height in CLBs")
    bit_parser.add_argument("--tracks", type=int, default=4, help="Tracks per channel")
    bit_parser.add_argument("--pins-per-side", type=int, default=4, help="Pins per CLB side")
    bit_parser.add_argument(
        "--fabric",
        dest="fabric_path",
        help="Fabric spec JSON file (overrides --w/--h/--tracks/--pins-per-side)",
    )
    bit_parser.add_argument(
        "--routing-dir",
        choices=["uni", "bi"],
        default="uni",
        help="Routing directionality (uni or bi)",
    )

    args = parser.parse_args()

    if args.cmd == "compile":
        src_path = Path(args.src)
        out_dir = Path(args.out_dir)
        text = src_path.read_text()
        module = parse_shdl(text)
        fabric_spec = _ensure_fabric_spec(args.fabric_path, out_dir)
        fnet = to_fnet(module, fabric=fabric_spec or None)
        out_path = out_dir / f"{module.name}.fnet.json"
        write_fnet(fnet, out_path)
        print(out_path)
    if args.cmd == "bit":
        src_path = Path(args.src)
        out_dir = Path(args.out_dir)
        text = src_path.read_text()
        module = parse_shdl(text)
        fabric_spec = _ensure_fabric_spec(args.fabric_path, out_dir)
        fnet = to_fnet(module, fabric=fabric_spec or None)
        mod = fnet["modules"][module.name]
        fabric = _load_fabric_spec(args, fabric_spec)
        placements = place_cells(mod["cells"], fabric)
        blocks = emit_blocks(mod["cells"], placements)
        routes = route_fnet(mod, fabric, placements)
        clb = build_clb_config(mod, placements, fabric)
        fbit = {
            "fabric": {
                "w": fabric.w,
                "h": fabric.h,
                "tracks": fabric.tracks,
                "pins_per_side": fabric.pins_per_side,
                "switch_box": fabric.switch_box,
                "cb_tracks": fabric.cb_tracks,
                "routing_dir": fabric.routing_dir,
                "turn_cost": fabric.turn_cost,
                "track_dirs": fabric.track_dirs,
                "slices_per_clb": fabric.slices_per_clb,
                "lut_k": fabric.lut_k,
            },
            "blocks": blocks,
            "routes": routes,
            "io": routes.get("io", {"in": [], "out": []}),
            "clb": clb,
        }
        out_dir.mkdir(parents=True, exist_ok=True)
        fnet_path = out_dir / f"{module.name}.fnet.json"
        fbit_path = out_dir / f"{module.name}.fbit.json"
        write_fnet(fnet, fnet_path)
        write_fbit(fbit, fbit_path)
        print(fbit_path)


if __name__ == "__main__":
    main()


def _read_fabric_spec(path: str | None) -> dict[str, object]:
    if not path:
        return {}
    spec_path = Path(path)
    return json.loads(spec_path.read_text())


def _ensure_fabric_spec(path: str | None, out_dir: Path) -> dict[str, object]:
    if path:
        return _read_fabric_spec(path)
    spec = _default_fabric_spec()
    out_dir.mkdir(parents=True, exist_ok=True)
    spec_path = out_dir / "default.fabric.json"
    if not spec_path.exists():
        spec_path.write_text(json.dumps(spec, indent=2, sort_keys=True) + "\n")
    return spec


def _load_fabric_spec(args: argparse.Namespace, spec: dict[str, object]) -> FabricSpec:
    return FabricSpec(
        w=int(spec.get("w", args.w)),
        h=int(spec.get("h", args.h)),
        tracks=int(spec.get("tracks", args.tracks)),
        pins_per_side=int(spec.get("pins_per_side", args.pins_per_side)),
        switch_box=str(spec.get("switch_box", "wilton")),
        cb_tracks=str(spec.get("cb_tracks", "all")),
        routing_dir=str(spec.get("routing_dir", args.routing_dir)),
        turn_cost=float(spec.get("turn_cost", 0.2)),
        track_dirs=spec.get("track_dirs"),
        slices_per_clb=int(spec.get("slices_per_clb", 4)),
        lut_k=int(spec.get("lut_k", 4)),
    )


def _default_fabric_spec() -> dict[str, object]:
    return {
        "w": 4,
        "h": 4,
        "tracks": 4,
        "pins_per_side": 4,
        "switch_box": "wilton",
        "cb_tracks": "all",
        "routing_dir": "uni",
        "turn_cost": 0.2,
        "track_dirs": {"e": 2, "w": 2, "n": 2, "s": 2},
        "slices_per_clb": 4,
        "lut_k": 4,
    }
