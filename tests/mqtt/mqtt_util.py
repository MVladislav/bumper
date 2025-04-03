"""Utilities for testing MQTT."""

from __future__ import annotations

import asyncio
import contextlib
import datetime
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from unittest.mock import Mock

    from aiomqtt import Client


async def verify_subscribe(
    test_client: Client,
    did: str,
    device_class: str,
    resource: str,
    mock: Mock,
    *,
    expected_called: bool,
) -> None:
    """Verify that a subscription works by publishing a test message."""
    command = "test"
    data = json.dumps({"test": str(datetime.datetime.now(datetime.UTC))}).encode("utf-8")
    topic = f"iot/atr/{command}/{did}/{device_class}/{resource}/j"

    # Subscribe to the topic
    await test_client.subscribe(topic)

    # Start listening for messages
    async def message_handler() -> None:
        async for message in test_client.messages:
            if message.topic.value == topic:
                mock(command, message.payload)

    # Start the message handler in the background
    handler_task = asyncio.create_task(message_handler())

    # Publish the test message
    await test_client.publish(topic, data)

    # Wait for the message to be received
    await asyncio.sleep(0.1)

    # Verify if the mock was called as expected
    if expected_called:
        mock.assert_called_with(command, data)
    else:
        mock.assert_not_called()

    # Cancel the message handler task
    handler_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await handler_task

    mock.reset_mock()
