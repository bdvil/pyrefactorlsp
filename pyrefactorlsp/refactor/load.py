import tomllib
from collections.abc import Mapping
from os import PathLike
from pathlib import Path
from typing import Any

from pyrefactorlsp.refactor.config import Config


class InvalidProjectError(Exception):
    pass


class InvalidPyprojectConfigError(Exception):
    pass


def find_project_file(path: PathLike | str) -> Path:
    path = Path(path)
    for file in path.iterdir():
        if file.is_file() and file.name == "pyproject.toml":
            return file
    if path.parent == path:
        raise InvalidProjectError
    return find_project_file(path.parent)


def get_project_name(pyproject: Mapping[str, Any]) -> str:
    """
    Returns the project name from the pyproject.toml file.
    It will first look in project.name, then in tool.poetry.name,
    in tool.pyrefactor.project_name, and finally if tool.pyrefactor.folders
    has only one element it will it as the name.

    Args:
        pyproject (`Mapping[str, Any]`): pyproject.toml object
    Returns:
        `str`: the project name
    """
    if "project" in pyproject and "name" in pyproject["project"]:
        return pyproject["project"]["name"]
    if "tool" in pyproject:
        if "poetry" in pyproject["tool"] and "name" in pyproject["tool"]["poetry"]:
            return pyproject["tool"]["poetry"]["name"]
        if (
            "pyrefactor" in pyproject["tool"]
            and "project_name" in pyproject["tool"]["pyrefactor"]
        ):
            return pyproject["tool"]["pyrefactor"]["project_name"]
        if (
            "pyrefactor" in pyproject["tool"]
            and "folders" in pyproject["tool"]["pyrefactor"]
            and len(pyproject["tool"]["pyrefactor"]["folders"]) == 1
        ):
            return pyproject["tool"]["pyrefactor"]["folders"][0]
    raise InvalidPyprojectConfigError


def get_pyrefactor_config(root: Path, pyproject: Mapping[str, Any]) -> Config:
    project_name = get_project_name(pyproject)
    if "tool" in pyproject and "pyrefactor" in pyproject["tool"]:
        pyproject["tool"]["pyrefactor"]["project_name"] = project_name
        pyproject["tool"]["pyrefactor"]["root"] = str(root.resolve())
        return Config.model_validate(pyproject["tool"]["pyrefactor"])
    return Config(project_name=project_name, root=str(root.resolve()))


def get_project_config(path: PathLike | str) -> Config:
    path = Path(path)
    project_file_path = find_project_file(path)
    with open(project_file_path, "rb") as f:
        pyproject = tomllib.load(f)
    return get_pyrefactor_config(project_file_path.parent, pyproject)
