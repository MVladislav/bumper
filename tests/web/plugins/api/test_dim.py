import asyncio
from unittest import mock

from aiohttp import web
from aiohttp.test_utils import TestClient
import pytest

from bumper.db import bot_repo
from bumper.mqtt.helper_bot import MQTTHelperBot


def async_return(result: web.Response) -> asyncio.Future:
    f = asyncio.Future()
    f.set_result(result)
    return f


@pytest.mark.usefixtures("clean_database", "helper_bot")
async def test_dim_devmanager(webserver_client: TestClient) -> None:
    # Test PollSCResult
    postbody = {"td": "PollSCResult"}
    async with webserver_client.post("/api/dim/devmanager.do", json=postbody) as resp:
        assert resp.status == 200
        test_resp = await resp.json()
        assert test_resp["ret"] == "ok"

    # Test HasUnreadMsg
    postbody = {"td": "HasUnreadMsg"}
    async with webserver_client.post("/api/dim/devmanager.do", json=postbody) as resp:
        assert resp.status == 200
        test_resp = await resp.json()
        assert test_resp["ret"] == "ok"
        assert test_resp["unRead"] is False

    # Test BotCommand
    bot_repo.add("sn_1234", "did_1234", "dev_1234", "res_1234", "eco-ng")
    bot_repo.set_mqtt("did_1234", True)
    postbody = {"toId": "did_1234"}

    # Test return fail timeout
    async with webserver_client.post("/api/dim/devmanager.do", json=postbody) as resp:
        assert resp.status == 200
        test_resp = await resp.json()
        assert test_resp["ret"] == "fail"
        assert test_resp["errno"] == 500
        assert test_resp["debug"] == "wait for response timed out"

    # Set bot not on mqtt
    bot_repo.set_mqtt("did_1234", False)
    async with webserver_client.post("/api/dim/devmanager.do", json=postbody) as resp:
        assert resp.status == 200
        test_resp = await resp.json()
        assert test_resp["ret"] == "fail"
        assert test_resp["debug"] == "requested bot is not supported"


@pytest.mark.usefixtures("clean_database")
async def test_dim_devmanager_faked(webserver_client: TestClient, helper_bot: MQTTHelperBot) -> None:
    # Test PollSCResult
    postbody = {"td": "PollSCResult"}
    async with webserver_client.post("/api/dim/devmanager.do", json=postbody) as resp:
        assert resp.status == 200
        test_resp = await resp.json()
        assert test_resp["ret"] == "ok"

    # Test HasUnreadMsg
    postbody = {"td": "HasUnreadMsg"}
    async with webserver_client.post("/api/dim/devmanager.do", json=postbody) as resp:
        assert resp.status == 200
        test_resp = await resp.json()
        assert test_resp["ret"] == "ok"
        assert test_resp["unRead"] is False

    # Test BotCommand
    bot_repo.add("sn_1234", "did_1234", "dev_1234", "res_1234", "eco-ng")
    bot_repo.set_mqtt("did_1234", True)
    postbody = {"toId": "did_1234"}

    # Test return get status
    command_getstatus_resp = {
        "id": "resp_1234",
        "resp": "<ctl ret='ok' status='idle'/>",
        "ret": "ok",
    }
    helper_bot.send_command = mock.MagicMock(return_value=async_return(web.json_response(command_getstatus_resp)))
    async with webserver_client.post("/api/dim/devmanager.do", json=postbody) as resp:
        assert resp.status == 200
        test_resp = await resp.json()
        assert test_resp["ret"] == "ok"
