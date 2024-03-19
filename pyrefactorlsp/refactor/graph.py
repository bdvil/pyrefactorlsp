from dataclasses import dataclass
from enum import StrEnum


class Graph[T]:
    def __init__(
        self,
        nodes: set[T] | None = None,
        edges: set[tuple[T, T]] | None = None,
    ):
        self.nodes: set[T] = nodes or set()
        self.edges: set[tuple[T, T]] = edges or set()

    def add_node(self, node: T) -> None:
        self.nodes.add(node)

    def add_edge(self, edge: tuple[T, T]) -> None:
        self.edges.add(edge)

    def remove_nodes(self, nodes: set[T]) -> None:
        for edge in self.edges.copy():
            if edge[0] in nodes or edge[1] in nodes:
                self.edges.remove(edge)
        self.nodes -= nodes

    def get_roots(self) -> set[T]:
        roots = set()
        for node in self.nodes:
            if not self.has_edge_to(node):
                roots.add(node)
        return roots

    def has_edge_from(self, node: T) -> bool:
        for source_node, _ in self.edges:
            if source_node == node:
                return True
        return False

    def has_edge_to(self, node: T) -> bool:
        for _, target_node in self.edges:
            if target_node == node:
                return True
        return False

    def children(self, node: T) -> set[T]:
        children = set()
        for source_node, target_node in self.edges:
            if source_node == node:
                children.add(target_node)
        return children

    def parents(self, node: T) -> set[T]:
        parents = set()
        for source_node, target_node in self.edges:
            if target_node == node:
                parents.add(source_node)
        return parents


class SymbolTypes(StrEnum):
    METHOD = "method"
    CLASS = "class"
    VARIABLE = "variable"


@dataclass
class Symbol:
    name: str
    kind: SymbolTypes


@dataclass
class Module:
    """
    Graph nodes are Modules.
    """

    url: str
    """URL to module"""

    text: str
    """Text content of the module"""

    symbols: set[Symbol]
