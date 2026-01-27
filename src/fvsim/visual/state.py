from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SBConnection:
    side_a: str
    track_a: int
    side_b: str
    track_b: int
    net: str | None = None


@dataclass(frozen=True)
class CBTap:
    side: str
    track: int
    pin: int
    net: str | None = None


@dataclass(frozen=True)
class SliceOutput:
    side: str
    pin: int
    use_ff: bool


@dataclass(frozen=True)
class IOPad:
    name: str
    x: int
    y: int
    side: str
    kind: str
    pin: int | None = None
    track: int | None = None
    net: str | None = None


@dataclass(frozen=True)
class Slice:
    index: int
    inputs: list[str]
    table: list[int]
    output: SliceOutput


@dataclass
class SBCell:
    x: int
    y: int
    connections: list[SBConnection] = field(default_factory=list)


@dataclass
class CBCell:
    x: int
    y: int
    side: str
    taps: list[CBTap] = field(default_factory=list)


@dataclass
class CLBCell:
    x: int
    y: int
    slices: list[Slice] = field(default_factory=list)


@dataclass
class FabricState:
    fabric: dict
    sb: dict[tuple[int, int], SBCell] = field(default_factory=dict)
    cb: dict[tuple[int, int, str], CBCell] = field(default_factory=dict)
    clb: dict[tuple[int, int], CLBCell] = field(default_factory=dict)
    io: list[IOPad] = field(default_factory=list)
