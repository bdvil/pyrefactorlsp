from pathlib import Path

from pyrefactorlsp.refactor.load import get_project_config

here = Path(__file__).parent


def test_load_project():
    config = get_project_config(here / "sample_project")
    assert config.project_name == "sample_project"
    assert config.root == str((here / "sample_project").resolve())
