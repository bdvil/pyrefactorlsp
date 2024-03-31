import libcst
from libcst.metadata import (
    MetadataWrapper,
    QualifiedNameProvider,
    QualifiedNameSource,
)

from pyrefactorlsp.refactor.module import Module


def get_module_name(node: libcst.BaseExpression) -> str:
    if isinstance(node, libcst.Name):
        return node.value
    if isinstance(node, libcst.Attribute):
        if isinstance(node.value, libcst.Name):
            return f"{node.value.value}.{node.attr.value}"
        return get_module_name(node.value) + "." + node.attr.value
    raise ValueError


class ImportedSymbolsCollector(libcst.CSTVisitor):
    METADATA_DEPENDENCIES = (QualifiedNameProvider,)

    def __init__(self):
        self.imported_symbols: set[str] = set()

    def visit_Name(self, node: libcst.Name) -> bool:
        qualified_names = self.get_metadata(QualifiedNameProvider, node, default=set())
        for name in qualified_names:
            if name.source == QualifiedNameSource.IMPORT:
                self.imported_symbols.add(name.name)
        return False

    def visit_Attribute(self, node: libcst.Attribute) -> bool:
        qualified_names = self.get_metadata(QualifiedNameProvider, node, default=set())
        if not len(qualified_names):
            return True
        for name in qualified_names:
            if name.source == QualifiedNameSource.IMPORT:
                self.imported_symbols.add(name.name)
        return False


def find_imports(module: Module) -> set[str]:
    wrapper = MetadataWrapper(module.cst)
    imported_symbols = ImportedSymbolsCollector()
    wrapper.visit(imported_symbols)
    return imported_symbols.imported_symbols
