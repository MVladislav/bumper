"""Api pim module plugin."""

from collections.abc import Iterable
from functools import cache
import logging
from pathlib import Path
from typing import Any

from bumper.utils.utils import load_json_array_files, load_json_object_files, load_text_files

_LOGGER = logging.getLogger(__name__)


@cache
def get_static_dir() -> Path:
    """Get base directory for static resources of this module."""
    return Path(__file__).parent


@cache
def get_bot_image_path() -> Path:
    """Get path to generic bot image."""
    return get_static_dir() / "robotvac_image.jpg"


@cache
def get_code_push_config() -> list[dict[str, Any]]:
    """Get code push config."""
    return load_json_array_files(["codePushConfig.json"], get_static_dir())


@cache
def get_config_groups_response() -> list[dict[str, Any]]:
    """Get config groups response."""
    return load_json_array_files(["configGroupsResponse.json", "configGroupsResponseUnofficial.json"], get_static_dir())


@cache
def get_config_net_all_response() -> list[dict[str, Any]]:
    """Get config net all response."""
    return load_json_array_files(["configNetAllResponse.json", "configNetAllResponseUnofficial.json"], get_static_dir())


@cache
def get_product_config_batch() -> list[dict[str, Any]]:
    """Get product config batch."""
    return load_json_array_files(["productConfigBatch.json"], get_static_dir())


@cache
def get_product_iot_map() -> list[dict[str, Any]]:
    """Get product IOT map combining official and unofficial mappings."""
    return load_json_array_files(["productIotMap.json", "productIotMapUnofficial.json"], get_static_dir())


@cache
def get_product_entry_group() -> list[dict[str, Any]]:
    """Get product entry group."""
    return load_json_array_files(["productEntryGroup.json"], get_static_dir())


@cache
def _get_config_groups_by_mid() -> dict[str, dict[str, Any]]:
    """Build a mid -> robot config lookup from the config groups response.

    The config groups response is a list of families, each with a ``robots`` list.
    Flatten it into a single mid-keyed dict so per-device lookups (e.g. for
    ``/product/info``) are O(1). Later duplicate mids win (unofficial overrides).
    """
    lookup: dict[str, dict[str, Any]] = {}
    for family in get_config_groups_response():
        for robot in family.get("robots", []):
            mid = robot.get("mid")
            if mid:
                lookup[mid] = robot
    return lookup


def _robot_to_product_info(robot: dict[str, Any]) -> dict[str, Any]:
    """Transform a config-groups robot entry into a ``/product/info`` object.

    The two endpoints serve the same underlying product data but with different
    envelopes: config groups exposes flat ``steps``/``qrpStep``/``cusSteps`` while
    ``/product/info`` nests them under ``configNetSteps``. Only the fields the
    wizard actually reads (mid, status, smartType, groupName) are guaranteed; the
    rest mirror the real cloud response for a faithful guide UX.
    """
    steps = robot.get("steps") or []
    config_net_steps: dict[str, Any] = {
        "qrpStep": robot.get("qrpStep", {}),
        "cusSteps": robot.get("cusSteps", {}),
    }
    for index, step in enumerate(steps, start=1):
        config_net_steps[f"step{index}"] = step

    group_name = robot.get("groupName", "")
    return {
        "id": robot.get("groupId", ""),
        "name": group_name,
        "groupName": group_name,
        "mid": robot.get("mid", ""),
        "smartType": robot.get("smartType", ""),
        "status": robot.get("status", "valid") or "valid",
        "snCfgNet": False,
        "materialNo": robot.get("materialNo", ""),
        "icon": robot.get("icon", ""),
        "failCount": robot.get("failCount", 0),
        "belongApp": robot.get("belongApp", []),
        "supportType": {"share": True},
        "configNetSteps": config_net_steps,
    }


def get_product_info_by_mids(mids: Iterable[str]) -> list[dict[str, Any]]:
    """Get ``/product/info`` objects for the given mids.

    Synthesized generically from the config groups data so any known device mid
    works, not just a hardcoded subset. Unknown mids are skipped (the real cloud
    likewise returns only resolvable entries).
    """
    lookup = _get_config_groups_by_mid()
    result: list[dict[str, Any]] = []
    for mid in mids:
        if robot := lookup.get(mid):
            result.append(_robot_to_product_info(robot))
    return result


@cache
def get_err_detail() -> list[dict[str, Any]]:
    """Get error detail json."""
    return load_json_array_files(["errDetail.json"], get_static_dir())


@cache
def get_common_area() -> dict[str, Any]:
    """Get common area json."""
    return load_json_object_files("commonArea.json", get_static_dir())


@cache
def get_codepush_update_check() -> dict[str, Any]:
    """Get codepush update check json."""
    return load_json_object_files("updateCheck.json", get_static_dir())


@cache
def get_codepush_update_check_mapping() -> dict[str, Any]:
    """Get codepush update check mapping json."""
    return load_json_object_files("updateCheck_mapping.json", get_static_dir())


@cache
def get_base_station_guide_newton_curi() -> str:
    """Get base station guide newton curi."""
    return load_text_files("BaseStationGuideNewtonCuri.html", get_static_dir())


@cache
def get_offline() -> str:
    """Get offline."""
    return load_text_files("Offline.html", get_static_dir())


@cache
def get_faq_problem() -> str:
    """Get faq problem."""
    return load_text_files("FaqProblem.html", get_static_dir())


@cache
def get_event_detail() -> str:
    """Get event detail."""
    return load_text_files("EventDetail.html", get_static_dir())
