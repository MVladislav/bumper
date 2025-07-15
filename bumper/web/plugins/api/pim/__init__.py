"""Api pim module plugin."""

import json
import logging
from pathlib import Path
from typing import Any

_LOGGER = logging.getLogger(__name__)


def get_code_push_config() -> list[dict[str, Any]]:
    """Get code push config."""
    return _load_json_files(["codePushConfig.json"])


def get_config_groups_response() -> list[dict[str, Any]]:
    """Get config groups response."""
    return _load_json_files(["configGroupsResponse.json", "configGroupsResponseUnofficial.json"])


def get_config_net_all_response() -> list[dict[str, Any]]:
    """Get config net all response."""
    return _load_json_files(["configNetAllResponse.json", "configNetAllResponseUnofficial.json"])


def get_product_config_batch() -> list[dict[str, Any]]:
    """Get product config batch."""
    return _load_json_files(["productConfigBatch.json"])


def get_product_iot_map() -> list[dict[str, Any]]:
    """Get product IOT map combining official and unofficial mappings."""
    return _load_json_files(["productIotMap.json", "productIotMapUnofficial.json"])


def _load_json_files(filenames: list[str | Path]) -> list[dict[str, Any]]:
    """Load and combine JSON arrays from one or more files located in the same directory as this module.

    :param filenames: List of JSON filenames (or Path objects) relative to this module.
    :return: Combined list of JSON objects.
    :raises TypeError: If any file does not contain a top-level JSON array.
    """
    base_path = Path(__file__).parent
    combined: list[dict[str, Any]] = []

    for fn in filenames:
        file_path = base_path / fn
        try:
            with file_path.open(encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            _LOGGER.exception(f"JSON file not found: {file_path}")
            raise
        except json.JSONDecodeError:
            _LOGGER.exception(f"Invalid JSON in file {file_path}")
            raise

        if not isinstance(data, list):
            msg = f"JSON file {file_path.name} must contain a top-level array."
            _LOGGER.error(msg)
            raise TypeError(msg)

        combined.extend(data)

    return combined
