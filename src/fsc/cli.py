from __future__ import annotations

import argparse
from pathlib import Path

from .emit import write_fnet
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

    args = parser.parse_args()

    if args.cmd == "compile":
        src_path = Path(args.src)
        out_dir = Path(args.out_dir)
        text = src_path.read_text()
        module = parse_shdl(text)
        fnet = to_fnet(module)
        out_path = out_dir / f"{module.name}.fnet.json"
        write_fnet(fnet, out_path)
        print(out_path)


if __name__ == "__main__":
    main()
