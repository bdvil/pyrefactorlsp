from collections.abc import Mapping, Sequence
from typing import Union

import libcst.matchers as m
from libcst import (
    Attribute,
    CSTTransformer,
    Import,
    ImportAlias,
    ImportFrom,
    ImportStar,
    MaybeSentinel,
    MetadataWrapper,
    Name,
    RemovalSentinel,
    RemoveFromParent,
    SimpleStatementLine,
)
from libcst import (
    Module as CSTModule,
)

from pyrefactorlsp.refactor.actions.move_symbol_source import MoveSymbolSource
from pyrefactorlsp.refactor.imports import ImportedSymbolsCollector
from pyrefactorlsp.refactor.module import Module


def seq_to_attr(name: Sequence[str]) -> Attribute | Name:
    """
    Transforms a sequence into a libcst Attribute

    Args:
        name (`Sequence[str]`):

    Returns:
        `Attribute | Name`:
    """
    head, tail = name[:-1], name[-1]
    if not len(head):
        return Name(tail)
    return Attribute(seq_to_attr(head), Name(tail))


def seq_to_attr_matcher(name: Sequence[str]) -> Union[m.Attribute, m.Name]:
    head, tail = name[:-1], name[-1]
    if not len(head):
        return m.Name(tail)
    return m.Attribute(seq_to_attr_matcher(head), m.Name(tail))


def join_attrs(x: Attribute | Name | None, y: Attribute | Name) -> Attribute | Name:
    if x is None:
        return y
    if isinstance(y, Name):
        return Attribute(x, y)
    if isinstance(y.value, (Attribute, Name)):
        return Attribute(join_attrs(x, y.value), y.attr)
    raise ValueError("Can't join attrs for given inputs")


class ReplaceImports(CSTTransformer):
    def __init__(self, imported_symbols: set[str], replace_imports: Mapping[str, str]):
        self.imported_symbols = imported_symbols
        print(imported_symbols)

        self._replace_imports: list[
            tuple[Union[m.Name, m.Attribute], Attribute | Name, str]
        ] = []
        for from_, to_ in replace_imports.items():
            path_from, _, obj_from = from_.rpartition(".")
            path_to, _, obj_to = to_.rpartition(".")
            if obj_from != obj_to:
                raise ValueError(f"{obj_from} should be same as {obj_to}")
            self._replace_imports.append(
                (
                    seq_to_attr_matcher(path_from.split(".")),
                    seq_to_attr(path_to.split(".")),
                    obj_from,
                )
            )
        self._imports_to_remove: set[ImportFrom | Import] = set()
        self._imports_to_add: set[ImportFrom | Import] = set()

    def should_be_replaced(
        self, prefix: Attribute | Name | None, name: ImportAlias
    ) -> tuple[Attribute | Name | None, str | None]:
        full_attr = join_attrs(prefix, name.name)
        for matcher_from, attr_to, obj in self._replace_imports:
            if m.matches(full_attr, matcher_from):
                return attr_to, obj
        return None, None

    def visit_Import(self, node: Import) -> bool | None:
        return

    def visit_ImportFrom(self, node: ImportFrom) -> bool | None:
        if node.module is None or len(node.relative):
            # TODO: Resolve relative path and use something similar to the
            # absolute import.
            return
        for matcher_from, attr_to, obj in self._replace_imports:
            if m.matches(node.module, matcher_from):
                if not isinstance(node.names, ImportStar):
                    self._imports_to_remove.add(node)
                    self._imports_to_add.add(
                        node.with_changes(
                            names=[
                                import_alias
                                for import_alias in node.names
                                if not m.matches(import_alias.name, m.Name(value=obj))
                            ]
                        )
                    )
                    self._imports_to_add.add(
                        ImportFrom(
                            module=attr_to,
                            names=[
                                import_alias.with_changes(comma=MaybeSentinel.DEFAULT)
                                for import_alias in node.names
                                if m.matches(import_alias.name, m.Name(value=obj))
                            ],
                        )
                    )
                else:
                    self._imports_to_add.add(
                        ImportFrom(
                            module=attr_to,
                            names=[ImportAlias(name=Name(value=obj))],
                        )
                    )

    def leave_Import(
        self, original_node: Import, updated_node: Import
    ) -> Import | RemovalSentinel:
        for node in self._imports_to_remove:
            if original_node == node:
                return RemoveFromParent()
        return updated_node

    def leave_ImportFrom(
        self, original_node: ImportFrom, updated_node: ImportFrom
    ) -> ImportFrom | RemovalSentinel:
        for node in self._imports_to_remove:
            if original_node == node:
                return RemoveFromParent()
        return updated_node

    def leave_Module(
        self, original_node: CSTModule, updated_node: CSTModule
    ) -> CSTModule:
        new_body = []
        for import_ in self._imports_to_add:
            new_body.append(SimpleStatementLine(body=[import_]))
        new_body.extend(updated_node.body)
        return updated_node.with_changes(body=new_body)


def move_symbol_target(
    target: Module, move_source: MoveSymbolSource, line: int, col: int
):
    """
    Finish moving a module

    Args:
        target (`Module`):
        move_source (`MoveSymbolSource`):
        line (`int`):
        col (`int`):
    """
    wrapper = MetadataWrapper(target.cst)
    imported_symbols = ImportedSymbolsCollector()
    wrapper.visit(imported_symbols)
