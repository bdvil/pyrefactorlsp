from difflib import ndiff
from pathlib import Path

from libcst import MetadataWrapper

from pyrefactorlsp.refactor.actions.move_symbol_target import ReplaceImports
from pyrefactorlsp.refactor.graph import build_project_graph
from pyrefactorlsp.refactor.load import get_project_config

here = Path(__file__).parent


def test_replace_imports():
    config = get_project_config(here / "sample_project")
    graph = build_project_graph(config)

    for node in graph.nodes:
        if node.name != "mod1":
            continue
        wrapper = MetadataWrapper(node.cst)
        import_replacer = ReplaceImports(
            {"sample_project.pkg.mod2.T": "sample_project.mod4.T"}
        )
        updated_node = wrapper.visit(import_replacer)
        print(
            "".join(
                ndiff(
                    node.cst.code.splitlines(keepends=True),
                    updated_node.code.splitlines(keepends=True),
                )
            ),
            end="",
        )


def test_replace_imports_import_from_mod():
    config = get_project_config(here / "sample_project")
    graph = build_project_graph(config)

    for node in graph.nodes:
        if node.name != "mod1_2":
            continue
        wrapper = MetadataWrapper(node.cst)
        import_replacer = ReplaceImports(
            {"sample_project.pkg.mod2.T": "sample_project.mod4.T"}
        )
        updated_node = wrapper.visit(import_replacer)
        print(
            "".join(
                ndiff(
                    node.cst.code.splitlines(keepends=True),
                    updated_node.code.splitlines(keepends=True),
                )
            ),
            end="",
        )


def test_replace_imports_absolute_import():
    config = get_project_config(here / "sample_project")
    graph = build_project_graph(config)

    for node in graph.nodes:
        if node.name != "mod1_3":
            continue
        wrapper = MetadataWrapper(node.cst)
        import_replacer = ReplaceImports(
            {"sample_project.pkg.mod2.T": "sample_project.mod4.T"}
        )
        updated_node = wrapper.visit(import_replacer)
        print(
            "".join(
                ndiff(
                    node.cst.code.splitlines(keepends=True),
                    updated_node.code.splitlines(keepends=True),
                )
            ),
            end="",
        )
