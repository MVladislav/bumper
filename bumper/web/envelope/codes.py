"""The codes the Ecovacs API answers with.

The modern API answers a failure with `code`, the legacy one with `errno`.
`0005` is the time skew code: the app learns the offset of the server clock
from the `time` field of the answer and replays the request once.
"""

RETURN_API_SUCCESS = "0000"

ERR_ACTIVATE_TOKEN_TIMEOUT = "1006"  # noqa: S105
ERR_COMMON = "0001"
ERR_DEFAULT = "9000"
ERR_EMAIL_NON_EXIST = "1002"
ERR_EMAIL_SEND_TIME_LIMIT = "1011"
ERR_EMAIL_USED = "1001"
ERR_INTERFACE_AUTH = "0002"
ERR_PARAM_INVALID = "0003"
ERR_PWD_WRONG = "1005"  # noqa: S105
ERR_RESET_PWD_TOKEN_TIMEOUT = "1007"  # noqa: S105
ERR_TIMESTAMP_INVALID = "0005"
ERR_TOKEN_INVALID = "0004"  # noqa: S105
ERR_USER_DISABLE = "1004"
ERR_USER_NOT_ACTIVATED = "1003"
ERR_WRONG_CONFIRM_PWD = "10010"  # noqa: S105
ERR_WRONG_EMAIL_ADDRESS = "1008"
ERR_WRONG_PWD_FROMATE = "1009"  # noqa: S105
ERR_UNKNOWN_TODO = "1202"
