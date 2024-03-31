from dataclasses import dataclass, field
from pathlib import Path

import libcst


@dataclass(frozen=True, eq=True)
class Symbol:
    name: str


@dataclass
class Module:
    """
    Graph nodes are Modules.
    """

    url: Path
    """URL to module"""

    package: str
    """Package of the module"""

    name: str
    """Name of the module"""

    text: str
    """Text content of the module"""

    cst: libcst.Module

    symbols: set[Symbol] = field(default_factory=set)

    @property
    def full_mod_name(self):
        return f"{self.package}.{self.name}"


def get_module(path: Path, package: str) -> Module:
    with open(path, "r") as f:
        text = f.read()
        cst = libcst.parse_module(text)

    return Module(url=path, package=package, name=path.stem, text=text, cst=cst)
