# Web API Endpoints

This guide explains how a web route chooses its response shape, how `@bind`
applies that shape, and which response template to start with when adding an
endpoint. The route must preserve the exact JSON keys, value types, and failure
shape expected by its client.

## 🧭 The pieces

| Piece                      | Job                                                                            |
| -------------------------- | ------------------------------------------------------------------------------ |
| `web.RouteTableDef`        | Registers paths and HTTP methods in one plugin module.                         |
| Route handler              | Reads the request, performs the operation, and returns the payload.            |
| `Template`                 | Describes the success envelope and its corresponding `ErrorShape`.             |
| `@bind(template)`          | Converts a handler's payload or `ApiError` into the endpoint's response shape. |
| `TypedDict` payload        | Names the fields and Python value types inside a response payload.             |
| `Operation` and `dispatch` | Selects a handler and template when one URL has several operations.            |

The template describes the JSON envelope. It does not validate the payload's
runtime type. Use type annotations and the payload definitions in
`bumper/web/payloads.py` to make the payload shape clear to mypy and tests.

## 🛣️ Register a route

Every plugin module owns a `web.RouteTableDef` named `routes`. The package
defines its prefix once in its `__init__.py`; modules use that prefix when
registering paths. The web plugin loader discovers plugin modules, so a new
module under `bumper/web/plugins/` does not need a second route-registration
edit.

```python
from aiohttp import web
from aiohttp.web_request import Request

from bumper.web.envelope import GL_V1, bind

from . import BASE_URL

routes = web.RouteTableDef()


@routes.view(f"{BASE_URL}user/getBackupEmailByAccount")
@bind(GL_V1)
async def _handle_get_backup_email_by_account(request: Request) -> dict[str, str | None]:
    """Return the backup email fields expected by this endpoint."""
    return {"backUpEmail": None, "displayEmail": None}
```

Decorators are applied from the bottom up: `bind` wraps the handler first,
then `routes.view` registers the wrapped handler. `routes.view` accepts any
HTTP method. Prefer `routes.get`, `routes.post`, and the other method-specific
registrations when the endpoint has a fixed method. Paths are case-sensitive.

A bound handler returns only the payload. It does not add `code`, `ret`,
`message`, `data`, or other envelope fields itself. The binder owns those
fields, including the error response shape.

## 📦 What `@bind` does

`bind` is implemented in `bumper/web/envelope/binder.py`:

1. It calls the handler with the `Request`.
2. If the handler returns a `StreamResponse` such as `web.Response`, it passes
   that response through unchanged. This is for files, images, and other raw
   documents.
3. Otherwise, it passes the returned payload to `Template.render` and returns
   the rendered JSON.
4. An `ApiError` is rendered using the template's `ErrorShape`, not its success
   shape. An uncaught exception is logged and returned with that error shape
   and HTTP status 500. `web.HTTPException` is re-raised.

For example, a handler bound to `GL_V1` can return `{"items": []}`. The client
receives the payload inside `data`, plus the `GL_V1` success fields. If the
handler raises `ApiError(msg="No account", code=ERR_TOKEN_INVALID)`, the same
route returns the `GL_V1` error envelope. The handler does not need to choose
either envelope itself.

Returning `web.json_response(...)` from a bound handler is usually wrong: it
bypasses the template and its error handling. Return a payload instead. Return
a `Response` only when the endpoint really is a raw response.

## 🧱 Template fields

`Template` is defined in `bumper/web/envelope/templates.py`. Its settings
control the outer shape:

| Setting              | Effect                                                                                                                         |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| `code`, `code_key`   | Adds a status value under a key such as `code`. Use `code=None` when there is no status field or the key carries payload data. |
| `data_key`           | Places the handler's payload under this key. `None` makes the payload flat.                                                    |
| `data_optional`      | Omits the payload key when the handler returns `None`. Otherwise, `None` is serialized as JSON `null`.                         |
| `flat`               | Merges a mapping payload into the response body instead of nesting it.                                                         |
| `result`             | Adds a fixed result pair such as `("ret", "ok")`.                                                                              |
| `msg`                | Adds a fixed message pair such as `("message", "success")`.                                                                    |
| `success`            | Adds the boolean `success` field when set.                                                                                     |
| `time`, `time_value` | Adds the current time in milliseconds, or a fixed time value.                                                                  |
| `todo`               | Adds `"todo": "result"`.                                                                                                       |
| `extra`              | Adds fixed side-car fields alongside the payload.                                                                              |
| `error`              | Selects the separate error envelope for the template.                                                                          |

`ErrorShape` controls failure keys such as `errno`, `error`, `ret`, `todo`,
`success`, and `time`. A success template and its error shape need not have the
same keys. Check both before using a template.

## 🧾 Choose the response shape

Start from the response contract of the endpoint or operation being added.
Choose the template by the JSON shape, not by which template name seems
cleanest.

| Client-visible response                                              | Use                                                  | Common location                                           |
| -------------------------------------------------------------------- | ---------------------------------------------------- | --------------------------------------------------------- |
| `code: "0000"`, `msg`, `data`, `success`, and millisecond `time`     | `GL_V1`                                              | Modern private API routes and global auth routes.         |
| `code: 0`, `message`, `ret: "ok"`, and `data`                        | `LEGACY`                                             | Standard `/api/...` JSON endpoints.                       |
| Legacy envelope without a success `ret` field                        | `LEGACY_NO_RET` or another matching `LEGACY` variant | Endpoints whose success response omits `ret`.             |
| Legacy envelope with a flat payload and `todo: "result"`             | `LEGACY_FLAT`                                        | `/api/users/user.do` operations.                          |
| Legacy envelope with `todo: "result"`, `ret: "ok"`, and `data`       | `TODO_RET`                                           | Older dispatcher endpoints such as `app.do`.              |
| `{"todo":"result","result":"ok","code":...}` where `code` is payload | `AUTH`                                               | The `newauth.do` auth-code exchange.                      |
| `{"ret":"ok"}` with no payload                                       | `RET_ONLY`                                           | Operations that answer only with a result flag.           |
| A file, image, or document body                                      | No template, or a bound handler returning `Response` | Photo downloads and document endpoints.                   |
| HTTP 200, empty body, outcome in `x-ngiot-*` headers                 | `response_ngiot_*` helpers                           | `/api/iot/endpoint/control`. This is not a JSON envelope. |

`LEGACY_BARE`, `LEGACY_MSG`, and `LEGACY_SUCCESS` cover other legacy variants.
Read their definitions and error shapes in `templates.py` rather than deriving
one from a similar-looking template.

### Typed payloads

The payload type is separate from the envelope template. Define or reuse a
`TypedDict` in `bumper/web/payloads.py` when a payload has named fields:

```python
from typing import TypedDict


class ExampleInfo(TypedDict):
    """The information returned by the example endpoint."""

    id: str
    enabled: bool


@routes.get(f"{PREFIX}/example/info")
@bind(LEGACY)
async def _handle_example_info(_: Request) -> ExampleInfo:
    """Return the example payload, not the legacy envelope."""
    return {"id": "example", "enabled": True}
```

Use `NotRequired[...]` for keys that are genuinely optional in the payload.
Do not make a field optional just because a value is unavailable in one test;
the response shape is part of the client contract. `Template.render` accepts
`Any` and does not enforce `TypedDict` at runtime, so keep the annotations,
builder, and tests aligned.

## 🔀 One path, several operations

Some endpoints select their behavior by `todo` or `td` in the request body.
Each operation can have a different response shape, so define an `Operation`
table and dispatch through it. Do not bind one envelope around the whole path.

```python
from collections.abc import Mapping
from typing import Any

from aiohttp import web
from aiohttp.web_request import Request
from bumper.web.envelope import LEGACY_FLAT
from bumper.web.operations import Operation, dispatch

from . import PREFIX

routes = web.RouteTableDef()
USER_DO_OPERATIONS: dict[str, Operation] = {}
routes.post(f"{PREFIX}/users/user.do")(dispatch(USER_DO_OPERATIONS, LEGACY_FLAT))


async def _handle_get_device_list(request: Request, post_body: Mapping[str, Any]) -> dict[str, Any]:
    """Return the payload for this user.do operation."""
    return {"devices": []}


USER_DO_OPERATIONS.update(
    {"GetDeviceList": Operation(LEGACY_FLAT, _handle_get_device_list)},
)
```

The dispatcher reads the configured discriminator, invokes the operation
handler, and renders its payload with that operation's template. The dispatcher
template is the failure shape for an unknown operation. Operation handlers
return payloads, not envelopes.

## ⚡ Quick checklist

Before implementing a route, answer these questions:

1. Is it a JSON envelope, a raw file/document response, or the NGIoT header
   protocol?
2. What exact success keys and value types does the client expect?
3. What exact failure shape does this endpoint use? Can the handler raise
   `ApiError` and let the binder shape it?
4. Does one path have multiple `todo`/`td` operations? If so, choose a template
   per operation with `dispatch`.
5. Does the payload have a reusable typed shape? Put that `TypedDict` or its
   builder in `bumper/web/payloads.py`.
6. Does the route path use the package prefix and the observed path casing?

If the answer shape is not known, do not invent a new template. Find an
existing matching operation or gather the missing response contract first.

## 🧪 Keep the response contract checked

- Put each route in the plugin module that owns the API path. Keep the route
  declaration near the handler or operation table.
- Add handler and payload tests under `tests/web/`, mirroring the source path.
- `scripts/api/api-table.py` shows each route's bound response shape.
- `tests/web/routes.txt` and `tests/web/shapes.txt` pin route registration and
  template selection. The pre-commit hook updates them when web routes change.
- `tests/web/response_shapes.json` and
  `tests/web/response_shapes_bumper.json` check response keys and Python value
  types. A new key or changed type needs a reason in the response contract.
- Run `uv run --active --frozen pytest tests/web`, the linters, and
  `uv run --active --frozen mkdocs build --strict` before contributing.

The core definitions are in `bumper/web/envelope/templates.py`,
`bumper/web/envelope/binder.py`, and `bumper/web/operations.py`.
