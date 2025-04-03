"""Webserver plugin module."""

from abc import abstractmethod
from collections.abc import Iterable
import inspect
import logging
from pathlib import Path
import sys
from types import ModuleType

from aiohttp import web
from aiohttp.web_routedef import AbstractRouteDef

_LOGGER = logging.getLogger(__name__)


class WebserverPlugin:
    """Abstract webserver plugin."""

    @property
    @abstractmethod
    def routes(self) -> Iterable[AbstractRouteDef]:
        """Plugin routes."""
        raise NotImplementedError


def _add_routes(app: web.Application, module: ModuleType, plugin_module_name: str) -> None:
    """Add routes from a module and its sub-modules to the web application."""
    if not module.__name__.startswith(plugin_module_name):
        return

    if module.__file__ is None:
        msg = "Module file is not available."
        raise ValueError(msg)

    module_path = Path(module.__file__)
    sub_app = web.Application() if module_path.name == "__init__.py" else app

    for _, clazz in inspect.getmembers(module, inspect.isclass):
        if issubclass(clazz, WebserverPlugin) and clazz != WebserverPlugin:
            web_obj: WebserverPlugin = clazz()
            sub_app.add_routes(web_obj.routes)
            _LOGGER.debug(f"Added routes from {clazz.__name__}")

    for _, obj in inspect.getmembers(module, inspect.ismodule):
        _add_routes(sub_app, obj, plugin_module_name)

    if module_path.name == "__init__.py":
        prefix = module_path.parent.as_posix()
        prefix = f"/{prefix[prefix.rfind('/') + 1 :]}/"
        app.add_subapp(prefix, sub_app)


def _import_plugins(module: ModuleType) -> None:
    """Import all plugins in a module."""
    if module.__file__ is None:
        msg = "Module file is not available."
        raise ValueError(msg)

    module_path = Path(module.__file__)
    plugin_files = [file for file in module_path.parent.glob("**/*.py") if file.is_file() and file != module_path]

    for file in plugin_files:
        plugin_name = None
        try:
            plugin_name = str(file).replace(str(Path().anchor), "").replace("/", ".")
            plugin_name = plugin_name[plugin_name.find(module.__name__) : -3].removesuffix(".__init__")
            imported_module = __import__(plugin_name, fromlist=["*"])
            _LOGGER.debug(f"Imported plugin module: {imported_module.__name__}")
        except Exception:
            _LOGGER.exception(f"Failed to import plugin module {plugin_name}")


def add_plugins(app: web.Application) -> None:
    """Discover and add all plugins to the web application."""
    module = sys.modules[__name__]
    _import_plugins(module)

    plugin_module_name = module.__name__
    for _, obj in inspect.getmembers(module, inspect.ismodule):
        if obj.__name__.startswith(plugin_module_name):
            _add_routes(app, obj, plugin_module_name)
