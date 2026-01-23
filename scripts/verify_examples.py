from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fsc.shdl import parse_shdl, to_fnet  # noqa: E402
from fvsim.load import load_design  # noqa: E402
from fvsim.sim import simulate  # noqa: E402


def main() -> None:
    _check_fnet("comb-2and")
    _check_fnet("dff-reg")
    _check_fnet("fanout")
    _check_sim_comb_2and()
    _check_sim_fanout()
    _check_sim_dff()
    print("ok")


def _load_example(name: str) -> Path:
    return ROOT / "docs" / "examples" / name


def _check_fnet(name: str) -> None:
    ex_dir = _load_example(name)
    shdl = ex_dir / "top.shdl"
    expected = ex_dir / "top.fnet.json"
    module = parse_shdl(shdl.read_text())
    actual = to_fnet(module)
    if actual != json.loads(expected.read_text()):
        raise AssertionError(f"fnet mismatch for {name}")


def _check_sim_comb_2and() -> None:
    ex_dir = _load_example("comb-2and")
    design = load_design(ex_dir / "top.fnet.json", ex_dir / "top.fbit.json")
    cases = [
        ({"a": "0", "b": "0"}, {"n1": "0", "y": "1"}),
        ({"a": "0", "b": "1"}, {"n1": "0", "y": "1"}),
        ({"a": "1", "b": "0"}, {"n1": "0", "y": "1"}),
        ({"a": "1", "b": "1"}, {"n1": "1", "y": "0"}),
    ]
    for inputs, expect in cases:
        result = simulate(design, inputs, ticks=1)[0].nets
        for net, val in expect.items():
            if result.get(net) != val:
                raise AssertionError(f"comb-2and {inputs} expected {net}={val}")


def _check_sim_fanout() -> None:
    ex_dir = _load_example("fanout")
    design = load_design(ex_dir / "top.fnet.json", ex_dir / "top.fbit.json")
    cases = [
        ({"a": "0", "b": "0"}, {"n1": "0", "y0": "0", "y1": "0"}),
        ({"a": "0", "b": "1"}, {"n1": "1", "y0": "0", "y1": "1"}),
        ({"a": "1", "b": "0"}, {"n1": "1", "y0": "1", "y1": "1"}),
        ({"a": "1", "b": "1"}, {"n1": "0", "y0": "0", "y1": "1"}),
    ]
    for inputs, expect in cases:
        result = simulate(design, inputs, ticks=1)[0].nets
        for net, val in expect.items():
            if result.get(net) != val:
                raise AssertionError(f"fanout {inputs} expected {net}={val}")


def _check_sim_dff() -> None:
    ex_dir = _load_example("dff-reg")
    design = load_design(ex_dir / "top.fnet.json", ex_dir / "top.fbit.json")
    inputs = [{"d": "0"}, {"d": "1"}, {"d": "0"}, {"d": "1"}]
    results = simulate(design, inputs, ticks=4)
    expected = ["0", "1", "0", "1"]
    for idx, expect in enumerate(expected):
        actual = results[idx].nets.get("q")
        if actual != expect:
            raise AssertionError(f"dff tick {idx} expected q={expect}")


if __name__ == "__main__":
    main()
