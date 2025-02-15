"""Api pim module plugin."""

import json
from pathlib import Path
from typing import Any


# EcoVacs Home Product IOT Map - 2023-10-08
# https://portal-ww.ecouser.net/api/pim/product/getProductIotMap
def get_product_iot_map() -> tuple[Any]:
    """Get product iot map."""
    with Path.open(
        Path(__file__).parent / "productIotMap.json",
        encoding="utf-8",
    ) as file:
        return (json.load(file),)
