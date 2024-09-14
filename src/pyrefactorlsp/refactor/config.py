from collections.abc import Sequence

from pydantic import BaseModel


class Config(BaseModel):
    root: str
    folders: Sequence[str] | None = None
    project_name: str
