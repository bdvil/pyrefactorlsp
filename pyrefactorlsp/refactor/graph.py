from importlib.util import resolve_name
from pathlib import Path

from pyrefactorlsp.refactor.config import Config
from pyrefactorlsp.refactor.imports import find_imports
from pyrefactorlsp.refactor.module import Module, Symbol, get_module


class Graph:
    def __init__(
        self,
        nodes: list[Module] | None = None,
        edges: list[tuple[Module, Module]] | None = None,
    ):
        self.nodes: list[Module] = nodes or []
        self.edges: list[tuple[Module, Module]] = edges or []

    def node_from_path(self, path: str) -> Module:
        for mod in self.nodes:
            if mod.full_mod_name == path:
                return mod
        raise ValueError(f"No module with path {path}")

    def add_node(self, node: Module) -> None:
        self.nodes.append(node)

    def add_edge(self, edge: tuple[Module, Module]) -> None:
        self.edges.append(edge)

    def remove_edge(self, edge: tuple[Module, Module]) -> None:
        return self.edges.remove(edge)

    def remove_nodes(self, nodes: list[Module]) -> None:
        for edge in self.edges.copy():
            if edge[0] in nodes or edge[1] in nodes:
                self.edges.remove(edge)
        for node in nodes:
            self.nodes.remove(node)

    def has_edge_from(self, node: Module) -> bool:
        for source_node, _ in self.edges:
            if source_node == node:
                return True
        return False

    def has_edge_to(self, node: Module) -> bool:
        for _, target_node in self.edges:
            if target_node == node:
                return True
        return False

    def children(self, node: Module) -> set[Module]:
        children = set()
        for source_node, target_node in self.edges:
            if source_node == node:
                children.add(target_node)
        return children

    def parents(self, node: Module) -> set[Module]:
        parents = set()
        for source_node, target_node in self.edges:
            if target_node == node:
                parents.add(source_node)
        return parents


def get_node_from_name(
    graph: Graph, name: str, current_pkg: str | None
) -> tuple[Module, str] | tuple[None, None]:
    mod, _, symbol = name.rpartition(".")
    mod = resolve_name(mod, current_pkg)
    for node in graph.nodes:
        if node.full_mod_name == mod:
            return node, symbol
        if node.full_mod_name == mod + ".__init__":
            return node, symbol
    return None, None


def get_module_dependencies(graph: Graph, module: Module) -> list[Module]:
    dependency_names = find_imports(module)
    dependencies: list[Module] = []
    for name in dependency_names:
        node, symbol = get_node_from_name(graph, name, module.package)
        if node is not None and symbol is not None:
            dependencies.append(node)
            module.symbols.add(Symbol(name=symbol))
    return dependencies


def add_nodes_to_graph(graph: Graph, path: Path, package: str | None = None) -> None:
    if package is None:
        package = ""
    for file in path.iterdir():
        file_package = package.split(".")
        file_package.append(file.name)
        if file.is_dir():
            add_nodes_to_graph(graph, file, ".".join(file_package))
        else:
            mod = get_module(file, package)
            graph.add_node(mod)


def add_edges_to_graph(graph: Graph):
    for mod in graph.nodes:
        dependencies = get_module_dependencies(graph, mod)
        for dependency in dependencies:
            graph.add_edge((mod, dependency))


def build_project_graph(config: Config) -> Graph:
    root = Path(config.root)
    graph: Graph = Graph()
    if config.folders is not None:
        for folder in config.folders:
            add_nodes_to_graph(graph, root / folder, folder)
    else:
        add_nodes_to_graph(graph, root)
    add_edges_to_graph(graph)
    return graph
