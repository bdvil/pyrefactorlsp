from collections import namedtuple
from collections.abc import Sequence
from difflib import SequenceMatcher

from lsprotocol.types import AnnotatedTextEdit, Position, Range, TextEdit

EditBlock = namedtuple("EditBlock", ["start", "length", "replacement"])


def get_diffs(original: str, updated: str) -> list[EditBlock]:
    matcher = SequenceMatcher(None, original, updated, False)
    matching_blocks = matcher.get_matching_blocks()
    unmatched_blocks: list[EditBlock] = []
    start = 0
    start_updated = 0
    for match in matching_blocks:
        if start == len(original):
            break
        replacement = updated[start_updated : match.b]
        length = match.a - start
        unmatched_blocks.append(EditBlock(start, length, replacement))
        start = match.a + match.size
        start_updated = match.b + match.size
    return unmatched_blocks


def str_index_to_line_offset(
    text: str, idx: Sequence[int]
) -> dict[int, tuple[int, int]]:
    locations: dict[int, tuple[int, int]] = {}
    cur_line, cur_offset = 0, 0
    for k, c in enumerate(text):
        if k in idx:
            locations[k] = (cur_line, cur_offset)
        if c == "\n":
            cur_line += 1
            cur_offset = 0
            continue
        cur_offset += 1
    return locations


def get_text_edits(original: str, update: str) -> list[TextEdit | AnnotatedTextEdit]:
    edit_blocks = get_diffs(original, update)
    print(edit_blocks)
    idx = []
    for block in edit_blocks:
        idx.append(block.start)
        idx.append(block.start + block.length)
    locations = str_index_to_line_offset(original, idx)

    return [
        TextEdit(
            new_text=block.replacement,
            range=Range(
                start=Position(
                    line=locations[block.start][0], character=locations[block.start][1]
                ),
                end=Position(
                    line=locations[block.start + block.length][0],
                    character=locations[block.start + block.length][1],
                ),
            ),
        )
        for block in edit_blocks
    ]
