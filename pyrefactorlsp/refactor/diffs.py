from difflib import SequenceMatcher
from typing import Literal


def get_diffs(s1: str, s2: str):
    matcher = SequenceMatcher(None, "", "", False)
    opcodes: list[
        list[tuple[Literal["delete", "insert", "replace", "equal"], int, int, int, int]]
    ] = []
    for x, y in zip(s1.split("\n"), s2.split("\n")):
        matcher.set_seqs(x, y)
        opcodes.append(matcher.get_opcodes())
    return opcodes
