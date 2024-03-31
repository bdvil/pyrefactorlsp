from pathlib import Path

from libcst import MetadataWrapper

from pyrefactorlsp.refactor.actions.move_symbol import RemoveSymbolFromSource
from pyrefactorlsp.refactor.graph import build_project_graph
from pyrefactorlsp.refactor.load import get_project_config

here = Path(__file__).parent


def test_remove_symbol():
    config = get_project_config(here / "sample_project")
    graph = build_project_graph(config)

    symbol_remover = RemoveSymbolFromSource(lineno=9, colno=3)

    for node in graph.nodes:
        if node.name != "mod1":
            continue
        wrapper = MetadataWrapper(node.cst)
        wrapper.visit(symbol_remover)
        assert symbol_remover.symbol is not None
        assert symbol_remover.symbol_name == "test_func"
        expected_needed_imports = {
            "sample_project.pkg.mod2.T",
            "sample_project.a",
            "<local>.y",
        }
        assert symbol_remover.needed_imports == expected_needed_imports
