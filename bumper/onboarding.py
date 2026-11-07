"""Coordinate an app Wi-Fi setup poll with a robot's first MQTT connection."""

from dataclasses import dataclass
import time
from typing import Any

WIFI_SETUP_TTL_SECONDS = 1800


@dataclass
class _WifiSetup:
    """An in-progress or completed Wi-Fi setup attempt."""

    setup_key: str
    user_id: str | None
    expires_at: float
    robot: dict[str, str] | None = None
    poll_key: str | None = None
    sync_key: str | None = None
    sync_did: str | None = None
    completed: bool = False


class WifiSetupManager:
    """Match one app setup poll to its authenticated MQTT bot and sync event."""

    def __init__(self) -> None:
        """Initialize the single active setup slot."""
        self._active: _WifiSetup | None = None

    def begin(self, setup_key: str, user_id: str | None = None) -> None:
        """Start or restart the setup attempt named by ``setup_key``."""
        self._active = _WifiSetup(
            setup_key=setup_key,
            user_id=user_id,
            expires_at=time.monotonic() + WIFI_SETUP_TTL_SECONDS,
        )

    def result(self, setup_key: str, user_id: str | None = None) -> dict[str, Any]:
        """Return the observed pending or success payload for a setup poll."""
        active = self._current()
        if active is not None and active.user_id == user_id:
            active.poll_key = setup_key
            self._complete_if_synced(active)
            if active.completed and active.robot is not None:
                return {"ret": "ok", **active.robot}
        return {
            "ret": "fail",
            "errno": 600,
            "subCode": 1,
            "debug": "Wi-Fi setup is waiting for the robot to connect",
        }

    def observe_sync_key(
        self,
        setup_key: str,
        *,
        did: str,
        name: str,
        robot_type: str,
        resource: str,
        sender_kind: str,
    ) -> None:
        """Record the sync key of the bot that is being set up."""
        active = self._current()
        if active is None:
            return
        sender_matches_setup_bot = (
            sender_kind == "bot"
            and all((did, name, robot_type, resource))
            and (active.poll_key is None or active.poll_key == setup_key)
        )
        if not sender_matches_setup_bot:
            return
        active.sync_key = setup_key
        active.sync_did = did
        active.robot = {
            "did": did,
            "name": name,
            "type": robot_type,
            "resource": resource,
        }
        self._complete_if_synced(active)

    @staticmethod
    def _complete_if_synced(active: _WifiSetup) -> None:
        """Complete only after the setup bot publishes the matching poll key."""
        active.completed = (
            active.robot is not None
            and active.poll_key is not None
            and active.sync_key == active.poll_key
            and active.sync_did == active.robot["did"]
        )

    def _current(self) -> _WifiSetup | None:
        """Return the active setup if it has not expired."""
        if self._active is not None and time.monotonic() >= self._active.expires_at:
            self._active = None
        return self._active


wifi_setup = WifiSetupManager()
