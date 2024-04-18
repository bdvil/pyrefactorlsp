from pyrefactorlsp.refactor.diffs import (
    get_diffs,
    get_text_edits,
    str_index_to_line_offset,
)


def update_str(s, r, start, end):
    new_s = s[:start]
    end_s = s[end:]
    new_s += r
    new_s += end_s
    return new_s


def test_diffs():
    s1 = "This is a text#with several lines#and some differences#in places."
    s2 = "This is a text#with many lines#and some differences# sometimes."
    blocks = get_diffs(s1, s2)
    for block in reversed(blocks):
        print(block)
        s1 = update_str(s1, block.replacement, block.start, block.start + block.length)
    assert s1 == s2


def test_index_to_line_offset():
    s1 = "This is a text\nwith several lines\nand some differences\nin places."
    line_offsets = str_index_to_line_offset(s1, [0, 5, 30, 50])
    assert line_offsets[0] == (0, 0)
    assert line_offsets[5] == (0, 5)
    assert line_offsets[30] == (1, 15)
    assert line_offsets[50] == (2, 16)


def test_get_text_edits():
    s1 = "This is a text\nwith several lines\nand some differences\nin places."
    s2 = "This is a text\nwith many lines\nand some differences\n sometimes."
    text_edits = get_text_edits(s1, s2)
    print(text_edits)
