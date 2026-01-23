from __future__ import annotations

Value = str


def not1(a: Value) -> Value:
    if a == "X":
        return "X"
    return "1" if a == "0" else "0"


def and2(a: Value, b: Value) -> Value:
    if a == "0" or b == "0":
        return "0"
    if a == "X" or b == "X":
        return "X"
    return "1"


def or2(a: Value, b: Value) -> Value:
    if a == "1" or b == "1":
        return "1"
    if a == "X" or b == "X":
        return "X"
    return "0"


def xor2(a: Value, b: Value) -> Value:
    if a == "X" or b == "X":
        return "X"
    return "1" if a != b else "0"

