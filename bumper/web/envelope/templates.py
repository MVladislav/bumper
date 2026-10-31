"""The response templates.

A template is the shape of a response, with the slots that the Ecovacs
API varies. The unit is the *operation* - the path plus the
`todo`/`td` discriminator inside the request - because one path can answer
in several shapes: `/api/iot/devmanager.do` answers `{"ret": "fail", …}` for
a robot command and `{"ret": "ok"}` for `td=PreWifiConfig`.

The app reads the envelope: `code` is a string, `msg` is a string and
`time` is a number of milliseconds, and the payload sits in `data`. The
legacy API accepts `code == "0000"`, else `ret == "ok"`, else `errno`.

The two generations of the API are the two families of the templates: the
modern one is served by the `gl-*` hosts (`GL_V1`), the legacy one by the
`*.ecouser.net` hosts (`LEGACY` and its variants, `TODO_RET` for the
endpoints that answer with a `todo`).
"""

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from typing import Any

from bumper.utils import utils

# The message on a successful response of the `gl-*` API. The app does
# not read it on success, so Bumper answers in English. The shop endpoints
# answer with a localized message, which is not implemented.
MSG_OPERATION_SUCCESS = "Operation Successful"


@dataclass(frozen=True, slots=True)
class ErrorShape:
    """The shape of a failed response.

    A family has one. The shape that a family fails with is named by the
    template of the family.
    """

    code_key: str = "errno"
    code: int | str = 1
    msg_key: str = "error"
    result: tuple[str, str] | None = None
    todo: bool = False
    success: bool | None = None
    time: bool = False
    extra: dict[str, Any] = field(default_factory=dict)

    def render(self, code: int | str | None = None, msg: str = "", debug: str = "") -> dict[str, Any]:
        """Render the error body."""
        body: dict[str, Any] = {}
        if self.result is not None:
            body[self.result[0]] = self.result[1]
        if self.todo:
            body["todo"] = "result"
        body[self.code_key] = self.code if code is None else code
        if msg:
            body[self.msg_key] = msg
        body.update(self.extra)
        if debug:
            body["debug"] = debug
        if self.success is not None:
            body["success"] = self.success
        if self.time:
            body["time"] = utils.get_current_time_as_millis()
        return body


@dataclass(frozen=True, slots=True)
class Template:
    """The shape of a successful response.

    Every slot has a default that says "not part of this shape", so a
    template reads like the JSON it produces.
    """

    # The `code` key. `None` omits it, which the auth endpoints need: there
    # the key carries the auth code, not a status.
    code: int | str | None = 0
    code_key: str = "code"
    # The key the payload goes under, and whether the key is left out when
    # the payload is `None`.
    data_key: str | None = "data"
    data_optional: bool = False
    # A flat answer: the payload is the body, not a value under a key.
    flat: bool = False
    # `("ret", "ok")` or `("result", "ok")`. The legacy API uses the first,
    # the two auth endpoints the second.
    result: tuple[str, str] | None = None
    # `("message", "success")` or `("msg", "success")`.
    msg: tuple[str, str] | None = None
    # The `success` key. The app does not read it, but the `gl-*` API
    # carries it.
    success: bool | None = None
    # The `time` key, stamped with the current time in milliseconds.
    time: bool = False
    # A fixed stamp, for the endpoints that report a time of their own.
    time_value: int | None = None
    # The `todo` key, which the legacy API carries as the literal "result".
    todo: bool = False
    # Side-car keys, e.g. the `configFAQ` object next to the payload.
    extra: dict[str, Any] = field(default_factory=dict)
    # The shape a failure of this family takes.
    error: ErrorShape = field(default_factory=ErrorShape)

    def with_data_key(self, data_key: str | None) -> "Template":
        """Return a copy that puts the payload under another key."""
        return replace(self, data_key=data_key)

    def with_code(self, code: int | str | None) -> "Template":
        """Return a copy with another code, or without one."""
        return replace(self, code=code)

    def with_result(self, result: tuple[str, str] | None) -> "Template":
        """Return a copy with another result key, or without one."""
        return replace(self, result=result)

    def with_msg(self, msg: tuple[str, str] | None) -> "Template":
        """Return a copy with another message key, or without one."""
        return replace(self, msg=msg)

    def with_time(self, value: int) -> "Template":
        """Return a copy that carries a fixed time."""
        return replace(self, time_value=value)

    def with_error(self, error: ErrorShape) -> "Template":
        """Return a copy that fails in another shape."""
        return replace(self, error=error)

    def with_success(self, success: bool | None) -> "Template":
        """Return a copy that carries the `success` key, or not."""
        return replace(self, success=success)

    def with_flat(self, flat: bool = True) -> "Template":
        """Return a copy that puts the payload in the body itself."""
        return replace(self, flat=flat)

    def with_optional_data(self, optional: bool = True) -> "Template":
        """Return a copy that leaves the payload out when it is `None`."""
        return replace(self, data_optional=optional)

    def with_side_car(self, key: str, value: Any) -> "Template":
        """Return a copy that carries an additional top level key."""
        merged = dict(self.extra)
        merged[key] = value
        return replace(self, extra=merged)

    def keys(self) -> set[str]:
        """Return the keys the shape adds, without the payload."""
        fixed: set[str] = set()
        if self.code is not None:
            fixed.add(self.code_key)
        if self.todo:
            fixed.add("todo")
        if self.result is not None:
            fixed.add(self.result[0])
        if self.msg is not None:
            fixed.add(self.msg[0])
        if self.success is not None:
            fixed.add("success")
        if self.time:
            fixed.add("time")
        fixed.update(self.extra)
        return fixed

    def render(self, data: Any = None) -> dict[str, Any]:
        """Render the body for `data`."""
        body: dict[str, Any] = {}
        if self.code is not None:
            body[self.code_key] = self.code
        if self.todo:
            body["todo"] = "result"
        if self.result is not None:
            body[self.result[0]] = self.result[1]
        if self.msg is not None:
            body[self.msg[0]] = self.msg[1]
        if self.flat:
            if isinstance(data, Mapping):
                body.update(data)
        elif self.data_key is not None and not (self.data_optional and data is None):
            body[self.data_key] = data
        if self.success is not None:
            body["success"] = self.success
        if self.time:
            body["time"] = self.time_value if self.time_value is not None else utils.get_current_time_as_millis()
        body.update(self.extra)
        return body


#: The `gl-*` API: `{"code": …, "msg": …, "time": …, "success": false}`.
ERROR_GL_V1 = ErrorShape(code_key="code", code="0001", msg_key="msg", success=False, time=True)

#: The `gl-*` API with the empty payload, which some endpoints carry.
ERROR_GL_V1_DATA = ErrorShape(
    code_key="code",
    code="0001",
    msg_key="msg",
    success=False,
    time=True,
    extra={"data": None},
)

#: The legacy `todo`/`ret` API: `{"todo": "result", "result": "fail",
#: "errno": …, "error": …}`.
ERROR_TODO_RET = ErrorShape(code_key="errno", code=1, msg_key="error", result=("result", "fail"), todo=True)

#: The legacy API when it answers with `ret` instead of `result`:
#: `{"ret": "fail", "errno": …, "error": …}`.
ERROR_TODO_RET_RET = ErrorShape(code_key="errno", code=1, msg_key="error", result=("ret", "fail"))

#: The legacy API with the debug field, which the bridge carries when the
#: robot is not reachable.
ERROR_TODO_RET_DEBUG = ErrorShape(
    code_key="errno",
    code=1,
    msg_key="error",
    result=("result", "fail"),
    todo=True,
    extra={"debug": ""},
)

#: The `api-app.*` API: `{"code": …, "ret": "fail", "todo": "result", "error": …}`.
ERROR_LEGACY = ErrorShape(code_key="code", code=1, msg_key="error", result=("ret", "fail"), todo=True)

#: The `api-app.*` API of the endpoints that carry the `success` key: the failure carries it as well.
ERROR_LEGACY_SUCCESS = ErrorShape(code_key="code", code=1, msg_key="message", success=False)

#: The legacy API for a todo it does not know: `{"todo": "result", "ret":
#: "fail", "err": 2004, "errno": 2004, "code": 2004}`.
ERROR_TODO_RET_UNKNOWN = ErrorShape(
    code_key="errno",
    code=2004,
    msg_key="err",
    result=("ret", "fail"),
    todo=True,
    extra={"err": 2004, "code": 2004},
)


#: The `gl-*` API: `{"code": "0000", "msg": …, "time": …, "data": …,
#: "success": true}`. The app reads `code`, `msg` and `time`, and learns
#: the clock offset from the last one when the server answers "0005".
GL_V1 = Template(
    code="0000",
    data_key="data",
    msg=("msg", MSG_OPERATION_SUCCESS),
    success=True,
    time=True,
    error=ERROR_GL_V1_DATA,
)

#: The `api-app.*` API: `{"code": 0, "message": "success", "ret": "ok",
#: "data": …}`. The `code` is a number here, not the "0000" of the `gl-*`
#: API, and the message key is `message`, not `msg`.
LEGACY = Template(
    code=0,
    data_key="data",
    msg=("message", "success"),
    result=("ret", "ok"),
    error=ERROR_LEGACY,
)

#: The `pim` API: `{"code": 0, "msg": "success", "data": …}`. The message
#: key is `msg` here, not the `message` of the other endpoints, and the
#: `ret` key is left out.
LEGACY_MSG = LEGACY.with_msg(("msg", "success")).with_result(None)

#: The `api-app.*` API without the `ret` key, which a few endpoints answer
#: without, and with the payload left out when it is empty.
LEGACY_BARE = LEGACY.with_result(None).with_msg(None)

#: The `api-app.*` API without the `ret` key, but with the message.
LEGACY_NO_RET = LEGACY.with_result(None)

#: The `api-app.*` API with the `success` key, which the app does not model
#: but the `gl-*` API carries on some endpoints.
LEGACY_SUCCESS = LEGACY.with_success(True).with_error(ERROR_LEGACY_SUCCESS)

#: The legacy `todo`/`ret` API: `{"code": 0, "todo": "result", "ret": "ok",
#: "data": …}`. The payload key varies per operation - `devices` on
#: `app.do`, `unRead` on `dim/devmanager.do`, `authCode` on `newauth.do`.
TODO_RET = Template(
    code=0,
    data_key="data",
    result=("ret", "ok"),
    todo=True,
    error=ERROR_TODO_RET,
)

#: The two auth endpoints: `{"todo": "result", "result": "ok", "code": …}`
#: where `code` carries the auth code, not a status.
AUTH = Template(
    code=None,
    data_key="code",
    result=("result", "ok"),
    todo=True,
    error=ERROR_TODO_RET,
)

#: A flat `{"ret": "ok"}`, which the legacy API answers for a few
#: operations that carry no payload.
RET_ONLY = Template(
    code=None,
    data_key=None,
    result=("ret", "ok"),
    error=ERROR_TODO_RET_RET,
)

#: The legacy API with the answer for a todo it does not know.
TODO_RET_UNKNOWN = TODO_RET.with_error(ERROR_TODO_RET_UNKNOWN)

#: A flat answer of the legacy API: the payload is the body, and the body
#: carries `{"todo": "result", "result": "ok"}` next to it.
LEGACY_FLAT = Template(
    code=None,
    data_key=None,
    result=("result", "ok"),
    todo=True,
    flat=True,
    error=ERROR_TODO_RET_DEBUG,
)


def describe(template: Template | None) -> str:
    """Return a readable name of the shape a template produces.

    The name of the family, and what it varies: the key of the payload, the
    keys it leaves out and the ones it adds.
    """
    if template is None:
        return "raw"
    names = {id(value): name for name, value in globals().items() if isinstance(value, Template)}
    parts = [names.get(id(template), "Template")]
    if template.data_key not in (None, "data"):
        parts.append(f"data_key={template.data_key}")
    if template.result is None:
        parts.append("no-ret")
    if template.msg is None:
        parts.append("no-message")
    if template.success is not None:
        parts.append("success")
    if template.extra:
        parts.append("side-car")
    if template.flat:
        parts.append("flat")
    return " ".join(parts)
