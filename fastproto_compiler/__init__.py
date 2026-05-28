"""fastproto compiler package."""

from importlib.metadata import PackageNotFoundError, version

from .generator import generate_code

try:
    __version__ = version("fastproto-compiler")
except PackageNotFoundError:
    __version__ = "0.0.0"

__all__ = ["__version__", "generate_code"]
