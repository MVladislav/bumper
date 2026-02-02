"""Api pim module plugin."""

from functools import cache
import logging
from pathlib import Path
from typing import Any

from bumper.utils.utils import load_json_array_files, load_json_object_files, load_text_files

_LOGGER = logging.getLogger(__name__)


@cache
def get_code_push_config() -> list[dict[str, Any]]:
    """Get code push config."""
    return load_json_array_files(["codePushConfig.json"], Path(__file__).parent)


@cache
def get_config_groups_response() -> list[dict[str, Any]]:
    """Get config groups response."""
    return load_json_array_files(["configGroupsResponse.json", "configGroupsResponseUnofficial.json"], Path(__file__).parent)


@cache
def get_config_net_all_response() -> list[dict[str, Any]]:
    """Get config net all response."""
    return load_json_array_files(["configNetAllResponse.json", "configNetAllResponseUnofficial.json"], Path(__file__).parent)


@cache
def get_product_config_batch() -> list[dict[str, Any]]:
    """Get product config batch."""
    return load_json_array_files(["productConfigBatch.json"], Path(__file__).parent)


@cache
def get_product_iot_map() -> list[dict[str, Any]]:
    """Get product IOT map combining official and unofficial mappings."""
    return load_json_array_files(["productIotMap.json", "productIotMapUnofficial.json"], Path(__file__).parent)


@cache
def get_common_area() -> dict[str, Any]:
    """Get common area json."""
    return load_json_object_files("commonArea.json", Path(__file__).parent)


@cache
def get_codepush_update_check() -> dict[str, Any]:
    """Get codepush update check json."""
    return load_json_object_files("updateCheck.json", Path(__file__).parent)


@cache
def get_base_station_guide_newton_curi() -> str:
    """Get base station guide newton curi."""
    return load_text_files("BaseStationGuideNewtonCuri.html", Path(__file__).parent)


@cache
def get_offline() -> str:
    """Get offline."""
    return load_text_files("Offline.html", Path(__file__).parent)


@cache
def get_faq_problem() -> str:
    """Get faq problem."""
    return load_text_files("FaqProblem.html", Path(__file__).parent)


@cache
def get_event_detail() -> str:
    """Get event detail."""
    return load_text_files("EventDetail.html", Path(__file__).parent)
