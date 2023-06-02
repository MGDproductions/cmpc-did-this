import importlib.resources
from pathlib import Path
from typing import ContextManager


def get_asset(asset: str) -> ContextManager[Path]:
    files = importlib.resources.files(__package__)
    traversable = files.joinpath("assets/").joinpath(asset)
    as_file = importlib.resources.as_file(traversable)
    return as_file
