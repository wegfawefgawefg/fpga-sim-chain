from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class Token:
    kind: str
    value: str
    line: int
    col: int


def tokenize(text: str) -> list[Token]:
    tokens: list[Token] = []
    line = 1
    col = 1
    i = 0
    while i < len(text):
        ch = text[i]
        if ch in " \t\r\n":
            if ch == "\n":
                line += 1
                col = 1
            else:
                col += 1
            i += 1
            continue
        if ch == ";":
            while i < len(text) and text[i] != "\n":
                i += 1
            continue
        if ch == "(":
            tokens.append(Token("LPAREN", ch, line, col))
            i += 1
            col += 1
            continue
        if ch == ")":
            tokens.append(Token("RPAREN", ch, line, col))
            i += 1
            col += 1
            continue
        start_col = col
        start = i
        while i < len(text) and text[i] not in " \t\r\n();":
            i += 1
            col += 1
        sym = text[start:i]
        tokens.append(Token("SYMBOL", sym, line, start_col))
    return tokens


def parse(tokens: Iterable[Token]) -> list:
    token_list = list(tokens)
    index = 0

    def parse_expr() -> object:
        nonlocal index
        if index >= len(token_list):
            raise ValueError("Unexpected end of input while parsing")
        tok = token_list[index]
        if tok.kind == "LPAREN":
            index += 1
            items: list[object] = []
            while index < len(token_list) and token_list[index].kind != "RPAREN":
                items.append(parse_expr())
            if index >= len(token_list):
                raise ValueError(f"Unclosed list starting at line {tok.line} col {tok.col}")
            index += 1
            return items
        if tok.kind == "RPAREN":
            raise ValueError(f"Unexpected ')' at line {tok.line} col {tok.col}")
        if tok.kind == "SYMBOL":
            index += 1
            return tok.value
        raise ValueError(f"Unknown token {tok.kind} at line {tok.line} col {tok.col}")

    exprs: list[object] = []
    while index < len(token_list):
        exprs.append(parse_expr())
    return exprs

