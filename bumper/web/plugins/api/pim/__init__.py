"""Api pim module plugin."""

import logging
from pathlib import Path
from typing import Any

from bumper.utils.utils import load_json_array_files

_LOGGER = logging.getLogger(__name__)


def get_code_push_config() -> list[dict[str, Any]]:
    """Get code push config."""
    return load_json_array_files(["codePushConfig.json"], Path(__file__).parent)


def get_config_groups_response() -> list[dict[str, Any]]:
    """Get config groups response."""
    return load_json_array_files(["configGroupsResponse.json", "configGroupsResponseUnofficial.json"], Path(__file__).parent)


def get_config_net_all_response() -> list[dict[str, Any]]:
    """Get config net all response."""
    return load_json_array_files(["configNetAllResponse.json", "configNetAllResponseUnofficial.json"], Path(__file__).parent)


def get_product_config_batch() -> list[dict[str, Any]]:
    """Get product config batch."""
    return load_json_array_files(["productConfigBatch.json"], Path(__file__).parent)


def get_product_iot_map() -> list[dict[str, Any]]:
    """Get product IOT map combining official and unofficial mappings."""
    return load_json_array_files(["productIotMap.json", "productIotMapUnofficial.json"], Path(__file__).parent)
