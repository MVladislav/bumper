"""Api pim module plugin."""

import json
import logging
from pathlib import Path
from typing import Any

_LOGGER = logging.getLogger(__name__)


def get_code_push_config() -> list[dict[str, Any]]:
    """Get code push config."""
    base_path = Path(__file__).parent
    json_file = base_path / "codePushConfig.json"

    with json_file.open(encoding="utf-8") as f1:
        product_config_batch: list[dict[str, Any]] = json.load(f1)
        return product_config_batch


def get_config_groups_response() -> list[dict[str, Any]]:
    """Get config groups response."""
    base_path = Path(__file__).parent
    json_file = base_path / "configGroupsResponse.json"

    with json_file.open(encoding="utf-8") as f1:
        product_config_batch: list[dict[str, Any]] = json.load(f1)
        return product_config_batch


def get_config_net_all_response() -> list[dict[str, Any]]:
    """Get config net all response."""
    base_path = Path(__file__).parent
    json_file = base_path / "configNetAllResponse.json"

    with json_file.open(encoding="utf-8") as f1:
        product_config_batch: list[dict[str, Any]] = json.load(f1)
        return product_config_batch


def get_product_config_batch() -> list[dict[str, Any]]:
    """Get product config batch."""
    base_path = Path(__file__).parent
    json_file = base_path / "productConfigBatch.json"

    with json_file.open(encoding="utf-8") as f1:
        product_config_batch: list[dict[str, Any]] = json.load(f1)
        return product_config_batch


# EcoVacs Home Product IOT Map - 2025-04-03
# https://portal-ww.ecouser.net/api/pim/product/getProductIotMap
def get_product_iot_map() -> list[dict[str, Any]]:
    """Get product iot map."""
    base_path = Path(__file__).parent
    product_iot_map_official = base_path / "productIotMap.json"
    product_iot_map_unofficial = base_path / "productIotMapUnofficial.json"

    with product_iot_map_official.open(encoding="utf-8") as f1, product_iot_map_unofficial.open(encoding="utf-8") as f2:
        map_official = json.load(f1)
        map_unofficial = json.load(f2)

    if not isinstance(map_official, list) or not isinstance(map_unofficial, list):
        msg = "Both JSON files must contain a JSON array at the top level."
        _LOGGER.error(msg)
        raise TypeError(msg)

    return map_official + map_unofficial
