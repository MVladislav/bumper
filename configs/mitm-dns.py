"""MitM Proxy DNS rewrite."""  # noqa: INP001

from mitmproxy import http


def request(flow: http.HTTPFlow) -> None:
    """Request."""
    if "codepush.appcenter.ms" in flow.request.pretty_url:
        # Replace target host but keep app's Host header
        flow.request.host = "codepush-base.dc-na.ww.ecouser.net"
        # print(f"🔧 Fixed CodePush: {flow.request.pretty_url}")


# def response(flow: http.HTTPFlow) -> None:
#     """Response."""
#     if "codepush.appcenter.ms" in flow.request.pretty_url:
#         print(f"✅ CodePush OK: {flow.response.status_code}")
