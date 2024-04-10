from pathlib import Path

from pyrefactorlsp.refactor.actions.move_symbol_source import move_symbol_source
from pyrefactorlsp.refactor.graph import build_project_graph
from pyrefactorlsp.refactor.load import get_project_config

here = Path(__file__).parent


def test_remove_symbol():
    config = get_project_config(here / "sample_project")
    graph = build_project_graph(config)

    lineno = 9
    colno = 3

    for node in graph.nodes:
        if node.name != "mod1":
            continue
        moved_symbol = move_symbol_source(node, lineno, colno)
        assert moved_symbol.symbol is not None
        assert moved_symbol.symbol_name == "test_func"
        expected_needed_imports = {
            "sample_project.pkg.mod2.T",
            "sample_project.a",
            "sample_project.mod1.y",
        }
        assert moved_symbol.needed_imports == expected_needed_imports
