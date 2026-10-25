"""The operations of an endpoint.

An endpoint that answers in more than one shape has one operation per
shape. The table names them, so a handler never names a family: it returns
the payload of its operation, and the dispatcher puts it in the shape the
operation declares.
"""

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
import logging
from typing import Any, Protocol, cast

from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import StreamResponse

from bumper.utils import utils
from bumper.web.context import read_body
from bumper.web.envelope import ApiError, Template

_LOGGER = logging.getLogger(__name__)

#: The payload of an operation, with the request it came from.
Handler = Callable[[Request, Mapping[str, Any]], Awaitable[Any]]


@dataclass(frozen=True, slots=True)
class Operation:
    """One operation of an endpoint: the shape of its answer and who answers."""

    template: Template
    handler: Handler


class Dispatcher:
    """The handler of an endpoint that answers in one shape per operation.

    The operation is picked by the discriminator in the body, and the answer
    is put in the shape that the operation declares. A request that names no
    operation fails in the shape of the endpoint.
    """

    def __init__(self, operations: Mapping[str, Operation], failure: Template, key: str = "todo") -> None:
        """Bind the operations of an endpoint to its route."""
        self.operations = operations
        self.failure = failure
        self.key = key

    async def __call__(self, request: Request) -> StreamResponse:
        """Answer the request with the shape of the operation it names."""
        try:
            body = await read_body(request)
            name = str(body.get(self.key, ""))
            operation = self.operations.get(name)
            if operation is None:
                msg = f"Error request, unknown {self.key}"
                raise ApiError(msg=msg, code=2004)
            result = await operation.handler(request, body)
        except ApiError as err:
            return web.json_response(self.failure.error.render(err.code, err.msg, err.debug))
        except Exception:
            _LOGGER.exception(utils.default_exception_str_builder(info="during handling request"))
            return web.json_response(self.failure.error.render(), status=500)

        if isinstance(result, StreamResponse):
            return result
        return web.json_response(operation.template.render(result))


class DispatchHandler(Protocol):
    """The handler of an endpoint that answers in one shape per operation.

    It carries the table of its operations, so the route table and the
    tests can read the shapes of the endpoint.
    """

    operations: Mapping[str, Operation]
    failure: Template

    def __call__(self, request: Request) -> Awaitable[StreamResponse]:
        """Answer the request with the shape of the operation it names."""


def dispatch(
    operations: Mapping[str, Operation],
    failure: Template,
    key: str = "todo",
) -> DispatchHandler:
    """Return the handler of an endpoint that answers in one shape per operation."""
    dispatcher = Dispatcher(operations, failure, key)

    async def handler(request: Request) -> StreamResponse:
        """Answer the request with the shape of the operation it names."""
        return await dispatcher(request)

    typed = cast("DispatchHandler", handler)
    typed.operations = operations
    typed.failure = failure
    return typed
