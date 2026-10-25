"""The errors of the response layer."""

from typing import Any


class ApiError(Exception):
    """A failure the endpoint knows about.

    The shape it takes is the one of the template the endpoint is bound to,
    so an endpoint reports a failure without naming a family. A failure is
    answered with http 200 and an error envelope, like the API does.
    """

    def __init__(self, msg: str = "", code: int | str | None = None, debug: str = "") -> None:
        """Init."""
        super().__init__(msg)
        self.msg = msg
        self.code = code
        self.debug = debug

    def render(self, template: Any) -> dict[str, Any]:
        """Render the error body with the shape of `template`."""
        body: dict[str, Any] = template.error.render(self.code, self.msg, self.debug)
        return body
