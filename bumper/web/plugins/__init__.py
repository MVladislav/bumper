"""The Ecovacs API surface.

Every module declares its routes with the full path, so the url of an
endpoint is written down where the endpoint is. The part that repeats over
the files of a package - the prefix - is written once, in the package, and
the modules build their paths from it.

The packages and the modules under them are found by walking this package,
so a new module is served without a second edit.
"""

from collections.abc import Iterator
import importlib
import logging
import pkgutil
from types import ModuleType

from aiohttp import web

_LOGGER = logging.getLogger(__name__)


def _modules(package: ModuleType) -> Iterator[ModuleType]:
    """Yield the modules of a package and of the packages under it."""
    for module_info in pkgutil.iter_modules(package.__path__):
        module = importlib.import_module(f"{package.__name__}.{module_info.name}")
        if module_info.ispkg:
            yield from _modules(module)
        else:
            yield module


def _packages() -> Iterator[ModuleType]:
    """Yield the packages that carry the API."""
    for module_info in pkgutil.iter_modules(__path__):
        if module_info.ispkg:
            yield importlib.import_module(f"{__name__}.{module_info.name}")


def plugin_modules() -> Iterator[ModuleType]:
    """Yield every module that carries routes."""
    for package in _packages():
        yield from _modules(package)


def add_plugins(app: web.Application) -> None:
    """Add the routes of every plugin module to the application."""
    for module in plugin_modules():
        routes = getattr(module, "routes", None)
        if routes is None:
            continue
        app.add_routes(routes)
        _LOGGER.debug(f"Added routes from {module.__name__}")
