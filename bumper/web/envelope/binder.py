"""The binder: a handler returns data, the binder shapes it.

The template is declared where the endpoint is declared, so the shape of a
response lives next to the path it answers. A handler never names a family.
"""

from collections.abc import Awaitable, Callable
import functools
import logging
from typing import Any

from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import StreamResponse

from bumper.utils import utils

from .errors import ApiError
from .templates import Template

_LOGGER = logging.getLogger(__name__)

Handler = Callable[[Request], Awaitable[Any]]


def bind(template: Template) -> Callable[[Handler], Handler]:
    """Bind a template to a handler.

    The handler returns the payload - a dict, a list, `None` - and the binder
    puts it in the shape of the template. A handler that returns a response
    itself is passed through, which is what the endpoints that serve a file
    or a document need.

    The template is kept on the wrapper, so the route table can be read
    without running the server: see `scripts/api/api-table.py`.
    """

    def decorator(handler: Handler) -> Handler:
        @functools.wraps(handler)
        async def wrapper(request: Request) -> StreamResponse:
            try:
                result = await handler(request)
            except ApiError as err:
                return web.json_response(template.error.render(err.code, err.msg, err.debug))
            except web.HTTPException:
                raise
            except Exception:
                _LOGGER.exception(utils.default_exception_str_builder(info="during handling request"))
                return web.json_response(template.error.render(), status=500)

            if isinstance(result, StreamResponse):
                return result
            return web.json_response(template.render(result))

        wrapper.template = template  # type: ignore[attr-defined]
        return wrapper

    return decorator
