from pyrefactorlsp.refactor.diffs import get_diffs


def test_diffs():
    s1 = "This is a text\nwith several lines\nand some differences\nin places."
    s2 = "This is a text\nwith many lines\nand some differences\n sometimes."
    opcodes = get_diffs(s1, s2)
    for k, opcode in enumerate(opcodes):
        print("Line", k, opcode)
