"""MitM Proxy Host Override with DNS."""  # noqa: INP001

from mitmproxy import http


def request(flow: http.HTTPFlow) -> None:
    """Override server address dynamically."""
    domain = "dc-na.ww.ecouser.net"
    if "codepush.appcenter.ms" in flow.request.pretty_url:
        flow.request.host = f"codepush-base.{domain}"
    if "adv-app.ecouser.net" in flow.request.pretty_url:
        flow.request.host = f"adv-app.{domain}"
    if "gl-de-wap.ecovacs.com" in flow.request.pretty_url:
        flow.request.host = f"gl-de-wap.{domain}"
