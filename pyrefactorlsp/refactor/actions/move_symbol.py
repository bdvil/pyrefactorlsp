import libcst.matchers as m
from libcst import (
    Attribute,
    ClassDef,
    CSTNode,
    CSTTransformer,
    FunctionDef,
    MetadataWrapper,
    Name,
    RemovalSentinel,
    RemoveFromParent,
    SimpleStatementLine,
)
from libcst.metadata import CodeRange, PositionProvider, QualifiedNameSource
from libcst.metadata.name_provider import QualifiedNameProvider

from pyrefactorlsp.refactor.module import Module


class RemoveSymbolFromSource(CSTTransformer):
    METADATA_DEPENDENCIES = (PositionProvider, QualifiedNameProvider)

    def __init__(self, lineno: int, colno: int):
        self.lineno = lineno
        self.colno = colno

        self._is_inside_symbol = False
        self.symbol: CSTNode | None = None
        self.symbol_name: str | None = None
        self.needed_imports: set[str] = set()

    def _is_in_range(self, code_range: CodeRange | None):
        """Checks whether the code_range is in given line and cols.

        Args:
            code_range (`CodeRange | None`):
        """
        if code_range is None:
            return False

        correct_line = code_range.start.line == self.lineno
        correct_column = code_range.start.column <= self.colno <= code_range.end.column
        return correct_line and correct_column

    def targetted_symbol(
        self, node: FunctionDef | ClassDef | SimpleStatementLine, node_name: str | None
    ) -> bool:
        """Visit Symbol, checks whether it's range. If it is, will register it as the
        symbol.

        Args:
            node (`FunctionDef | ClassDef`):

        Returns:
            `bool`: whether this is the targetted symbol
        """
        if self._is_inside_symbol:
            return False
        code_range = self.get_metadata(PositionProvider, node, None)
        if self._is_in_range(code_range):
            self._is_inside_symbol = True
            self.symbol = node
            self.symbol_name = node_name
            return True
        return False

    def visit_FunctionDef(self, node: FunctionDef) -> bool | None:
        self.targetted_symbol(node, node.name.value)

    def visit_ClassDef(self, node: ClassDef) -> bool | None:
        self.targetted_symbol(node, node.name.value)

    def visit_SimpleStatementLine(self, node: SimpleStatementLine) -> bool | None:
        # matcher = m.SimpleStatementLine(body=[m.Assign() | m.AnnAssign()])
        # if m.matches(node, matcher):
        #     self.targetted_symbol(node, None)
        pass

    def leave_symbol(
        self,
        original_node: FunctionDef | ClassDef | SimpleStatementLine,
        updated_node: FunctionDef | ClassDef | SimpleStatementLine,
    ) -> FunctionDef | ClassDef | SimpleStatementLine | RemovalSentinel:
        """When leaving the symbol, will remove from module if it's the one to move.

        Args:
            original_node (`FunctionDef | ClassDef`):
            updated_node (`FunctionDef | ClassDef`):

        Returns:
            `FunctionDef | ClassDef | RemovalSentinel`:
        """
        if original_node == self.symbol:
            self._is_inside_symbol = False
            return RemoveFromParent()
        return updated_node

    def leave_FunctionDef(
        self, original_node: FunctionDef, updated_node: FunctionDef
    ) -> FunctionDef | ClassDef | SimpleStatementLine | RemovalSentinel:
        return self.leave_symbol(original_node, updated_node)

    def leave_ClassDef(
        self, original_node: ClassDef, updated_node: ClassDef
    ) -> FunctionDef | ClassDef | SimpleStatementLine | RemovalSentinel:
        return self.leave_symbol(original_node, updated_node)

    def leave_SimpleStatementLine(
        self, original_node: SimpleStatementLine, updated_node: SimpleStatementLine
    ):
        # return self.leave_symbol(original_node, updated_node)
        return updated_node

    def _add_needed_imports(self, node: Name | Attribute) -> bool:
        """Adds required imports for the symbol in the list.

        Args:
            node (`Name | Attribute`): Name or Attribute node to check

        Returns:
            `bool`: whether to keep visiting children
        """
        qualified_names = self.get_metadata(QualifiedNameProvider, node, default=set())
        if not len(qualified_names):
            return True
        for name in qualified_names:
            if name.source == QualifiedNameSource.IMPORT:
                self.needed_imports.add(name.name)
            elif (
                name.source == QualifiedNameSource.LOCAL
                and name.name != self.symbol_name
            ):
                parts = name.name.split(".")
                # Do not include local defs
                if parts[0] == self.symbol_name:
                    continue
                self.needed_imports.add(f"<local>.{name.name}")
        return False

    def visit_Name(self, node: Name) -> bool:
        if not self._is_inside_symbol:
            return True
        return self._add_needed_imports(node)

    def visit_Attribute(self, node: Attribute) -> bool:
        if not self._is_inside_symbol:
            return True
        return self._add_needed_imports(node)


def move_symbol(start: Module, end: Module, line: int, col: int):
    """
    Move symbol from start module to end module and update all imports.
    """
    wrapper = MetadataWrapper(start.cst)
    symbole_remover = RemoveSymbolFromSource(line, col)
    wrapper.visit(symbole_remover)
