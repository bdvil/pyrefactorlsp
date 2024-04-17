from collections.abc import Iterable, Mapping, Sequence
from typing import Union

import libcst.matchers as m
from libcst import (
    Attribute,
    BaseCompoundStatement,
    ClassDef,
    CSTTransformer,
    FunctionDef,
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
from libcst.metadata import (
    PositionProvider,
    QualifiedNameProvider,
    QualifiedNameSource,
)

from pyrefactorlsp.refactor.actions.move_symbol_source import MoveSymbolSource
from pyrefactorlsp.refactor.graph import Graph
from pyrefactorlsp.refactor.imports import get_module_name
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
    METADATA_DEPENDENCIES = (QualifiedNameProvider,)

    def __init__(
        self,
        replace_imports: Mapping[str, str],
        add_imports: Iterable[str] | None = None,
        remove_imports: Iterable[str] | None = None,
    ):
        self.imported_symbols: set[str] = set()

        self._replace_import_map = replace_imports

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
        self._imports_to_add: dict[frozenset[str], ImportFrom | Import] = {}

        self._update_attr: dict[Name | Attribute, Name] = {}

        if add_imports is not None:
            for add_import in add_imports:
                module, _, obj = add_import.rpartition(".")
                self._add_import(module, obj)
        if remove_imports is not None:
            for remove_import in remove_imports:
                module, _, obj = remove_import.rpartition(".")
                self._remove_import(module, obj)

    def _add_import(self, module: str, obj: str):
        obj_key = frozenset([obj])
        if obj_key in self._imports_to_add:
            return
        self._imports_to_add[obj_key] = ImportFrom(
            module=seq_to_attr(module.split(".")),
            names=[ImportAlias(name=Name(value=obj))],
        )

    def _remove_import(self, module: str, obj: str):
        self._imports_to_remove.add(
            ImportFrom(
                module=seq_to_attr(module.split(".")),
                names=[ImportAlias(name=Name(value=obj))],
            )
        )

    def visit_Name(self, node: Name) -> bool:
        qualified_names = self.get_metadata(QualifiedNameProvider, node, default=set())
        for name in qualified_names:
            if (
                name.source == QualifiedNameSource.IMPORT
                and name.name in self._replace_import_map
            ):
                module, _, obj = name.name.rpartition(".")
                self._add_import(module, obj)
                self._update_attr[node] = Name(value=obj)
                return False
        return True

    def visit_Attribute(self, node: Attribute) -> bool:
        qualified_names = self.get_metadata(QualifiedNameProvider, node, default=set())
        for name in qualified_names:
            if (
                name.source == QualifiedNameSource.IMPORT
                and name.name in self._replace_import_map
            ):
                module, _, obj = name.name.rpartition(".")
                self._add_import(module, obj)
                self._update_attr[node] = Name(value=obj)
                return False
        return True

    def leave_Attribute(
        self, original_node: Attribute, updated_node: Attribute
    ) -> Name | Attribute:
        if original_node in self._update_attr:
            return self._update_attr[original_node]
        return updated_node

    def leave_Name(self, original_node: Name, updated_node: Name) -> Name:
        if original_node in self._update_attr:
            return self._update_attr[original_node]
        return updated_node

    def should_be_replaced(
        self, prefix: Attribute | Name | None, name: ImportAlias
    ) -> tuple[Attribute | Name | None, str | None]:
        full_attr = join_attrs(prefix, name.name)
        for matcher_from, attr_to, obj in self._replace_imports:
            if m.matches(full_attr, matcher_from):
                return attr_to, obj
        return None, None

    def visit_ImportFrom(self, node: ImportFrom) -> bool | None:
        if node.module is None or len(node.relative):
            # TODO: Resolve relative path and use something similar to the
            # absolute import.
            return
        for matcher_from, attr_to, obj in self._replace_imports:
            if m.matches(node.module, matcher_from):
                if not isinstance(node.names, ImportStar):
                    self._imports_to_remove.add(node)
                    import_aliases = []
                    import_names = []
                    for import_alias in node.names:
                        if not m.matches(import_alias.name, m.Name(value=obj)):
                            import_aliases.append(import_alias)
                            import_names.append(get_module_name(import_alias.name))
                    self._imports_to_add[frozenset(import_names)] = node.with_changes(
                        names=import_aliases
                    )
                    self._imports_to_add[frozenset([obj])] = ImportFrom(
                        module=attr_to,
                        names=[
                            import_alias.with_changes(comma=MaybeSentinel.DEFAULT)
                            for import_alias in node.names
                            if m.matches(import_alias.name, m.Name(value=obj))
                        ],
                    )
                else:
                    self._imports_to_add[frozenset([obj])] = ImportFrom(
                        module=attr_to,
                        names=[ImportAlias(name=Name(value=obj))],
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
        for import_ in self._imports_to_add.values():
            new_body.append(SimpleStatementLine(body=[import_]))
        new_body.extend(updated_node.body)
        return updated_node.with_changes(body=new_body)


class AddSymbol(CSTTransformer):
    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(
        self, lineno: int, symbol: FunctionDef | ClassDef | SimpleStatementLine
    ):
        self.lineno = lineno

        self.symbol = symbol

    def _is_after(self, line: SimpleStatementLine | BaseCompoundStatement):
        """Checks whether the code_range is after the given line number.

        Args:
            code_range (`CodeRange | None`):
        """
        code_range = self.get_metadata(PositionProvider, line, None)
        if code_range is None:
            return False

        return code_range.start.line >= self.lineno

    def leave_Module(
        self, original_node: CSTModule, updated_node: CSTModule
    ) -> CSTModule:
        new_body: list[SimpleStatementLine | BaseCompoundStatement] = []
        is_added = False
        for line in updated_node.body:
            if not is_added and self._is_after(line):
                new_body.append(self.symbol)
                is_added = True
            new_body.append(line)

        return updated_node.with_changes(body=new_body)


def move_symbol_target(
    graph: Graph,
    target: Module,
    move_source: MoveSymbolSource,
    line: int,
) -> list[Module]:
    """
    Finish moving a module

    Args:
        graph (`Graph`): dependency graph
        target (`Module`):
        move_source (`MoveSymbolSource`):
        line (`int`): line to add the element to
    Returns:
        `list[Module]`: list of edited modules
    """
    if move_source.symbol_name is None or move_source.symbol is None:
        return []
    source_name = move_source.source_mod.full_mod_name + "." + move_source.symbol_name
    target_name = target.full_mod_name + "." + move_source.symbol_name
    wrapper = MetadataWrapper(target.cst)
    import_replacer = ReplaceImports({}, move_source.needed_imports, {source_name})
    updated_target = wrapper.visit(import_replacer)
    wrapper = MetadataWrapper(updated_target)
    add_symbol = AddSymbol(line, move_source.symbol)
    move_source.source_mod.cst = move_source.updated_source
    target.cst = wrapper.visit(add_symbol)
    edited_modules = [move_source.source_mod, target]

    for new_dep in move_source.needed_imports:
        print(new_dep)
        new_dep_mod = graph.node_from_path(new_dep)
        graph.add_edge((target, new_dep_mod))
    graph.remove_edge((graph.node_from_path(source_name), target))

    for dependent_mod in graph.children(move_source.source_mod):
        wrapper = MetadataWrapper(dependent_mod.cst)
        import_replacer = ReplaceImports({source_name: target_name})
        dependent_mod.cst = wrapper.visit(import_replacer)
        graph.remove_edge((graph.node_from_path(source_name), dependent_mod))
        graph.add_edge((graph.node_from_path(target_name), dependent_mod))
        edited_modules.append(dependent_mod)
    return edited_modules
