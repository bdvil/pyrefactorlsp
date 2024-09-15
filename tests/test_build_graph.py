from pathlib import Path

from pyrefactorlsp.refactor.graph import build_project_graph
from pyrefactorlsp.refactor.load import get_project_config

here = Path(__file__).parent


expected_graph_edges = {
    ("sample_project.mod1", "sample_project.pkg.mod2"),
    ("sample_project.mod1", "sample_project.__init__"),
    ("sample_project.mod1", "sample_project.mod4"),
    ("sample_project.pkg.mod2", "sample_project.pkg.subpkg.mod3"),
    ("sample_project.pkg.mod2", "sample_project.mod4"),
    ("sample_project.mod1_2", "sample_project.__init__"),
    ("sample_project.mod1_2", "sample_project.mod4"),
    ("sample_project.mod1_2", "sample_project.pkg.mod2"),
    ("sample_project.mod1_3", "sample_project.__init__"),
    ("sample_project.mod1_3", "sample_project.mod4"),
    ("sample_project.mod1_3", "sample_project.pkg.mod2"),
}


def test_add_nodes():
    config = get_project_config(here / "sample_project")
    graph = build_project_graph(config)
    graph_edges = set()
    for edge_start, edge_end in graph.edges:
        graph_edges.add((edge_start.full_mod_name, edge_end.full_mod_name))
    assert expected_graph_edges == graph_edges
