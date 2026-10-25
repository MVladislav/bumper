"""The hosts of the services the app talks to.

Every service of the API is served by the same server, so the answer names
the service and the domain it belongs to. The region of the cloud is not
part of the answer by default - a self hosted server has no shards - but it
can be put back with `DOM_SUB_1`, `DOM_SUB_2` and `DOM_SUB_3` for the setups
that need the shard of a region.

Two names keep more than the service:

- the broker of the MQTT keeps its name, because the router of the compose
  files sends every host with an `mq` in it to the MQTT port,
- the broker of the XMPP comes with the port it listens on.
"""

from bumper.utils.settings import config as bumper_isc


def api_host(name: str, domain: str, region: str = "") -> str:
    """Return the host of a service.

    The region is the infix of the cloud, e.g. `dc-eu.ww.`, and it is empty
    unless a setup asks for it.
    """
    return f"{name}.{region}{domain}"


def adv_host() -> str:
    """Return the host that serves the pages of the store."""
    return api_host("adv-app", bumper_isc.DOMAIN_MAIN, bumper_isc.DOM_SUB_1)


def pim_host() -> str:
    """Return the host that serves the files of the pim service."""
    return api_host("api-app", bumper_isc.DOMAIN_MAIN, bumper_isc.DOM_SUB_1)


def wap_host() -> str:
    """Return the host that serves the pages of the app."""
    return api_host("gl-US-wap", bumper_isc.DOMAIN_SEC3)


def codepush_host() -> str:
    """Return the host that serves the CodePush service."""
    return api_host("codepush-base", bumper_isc.DOMAIN_MAIN, bumper_isc.DOM_SUB_1)


def xmpp_host(name: str, domain: str) -> str:
    """Return the host of the XMPP broker, with the port it listens on."""
    return f"{name}.{domain}:{bumper_isc.XMPP_LISTEN_PORT_TLS}"


def photo_url(host: str, photo_id: str) -> str:
    """Return the URL of an uploaded image as an SVG document."""
    return f"https://{host}/api/photo/download?id={photo_id}&format=svg"


def placeholder_photo_url(host: str) -> str:
    """Return the URL of the image that stands in for a missing map.

    The app expects a download URL for every job, so a job without a stored
    map points at the shared placeholder instead of an empty string.
    """
    return f"https://{host}/api/photo/download?format=svg"
