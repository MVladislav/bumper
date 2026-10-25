from pathlib import Path
from unittest.mock import patch

from aiohttp.test_utils import TestClient
import pytest

from bumper.db import bot_repo, clean_log_repo, photo_repo, user_repo
from bumper.web.utils.models import CleanLog


@pytest.mark.usefixtures("clean_database", "mqtt_server")
async def test_restart_mqtt_server(webserver_client: TestClient) -> None:
    async with webserver_client.get("/restart_MQTTServer") as resp:
        assert resp.status == 200


@pytest.mark.usefixtures("clean_database", "xmpp_server")
async def test_restart_xmpp_server(webserver_client: TestClient) -> None:
    async with webserver_client.get("/restart_XMPPServer") as resp:
        assert resp.status == 200


async def test_remove_bot(webserver_client: TestClient) -> None:
    async with webserver_client.get("/bot/remove/test_did") as resp:
        assert resp.status == 200


async def test_remove_client(webserver_client: TestClient) -> None:
    async with webserver_client.get("/client/remove/test_resource") as resp:
        assert resp.status == 200


async def test_remove_user(webserver_client: TestClient) -> None:
    async with webserver_client.get("/user/remove/test_resource") as resp:
        assert resp.status == 200


async def test_remove_clean_log(webserver_client: TestClient) -> None:
    async with webserver_client.get("/clean_log/remove/test_resource") as resp:
        assert resp.status == 200


async def test_remove_clean_logs(webserver_client: TestClient) -> None:
    async with webserver_client.get("/clean_logs/remove/test_resource") as resp:
        assert resp.status == 200


async def test_handle_partial(webserver_client: TestClient) -> None:
    async with webserver_client.get("/server-status") as resp:
        assert resp.status == 200
        content_type = resp.headers.get("Content-Type", "")
        assert content_type.startswith("text/html")
        assert resp.content_length > 0
        # assert await resp.read()


@pytest.mark.usefixtures("clean_database")
async def test_the_page_holds_every_section(webserver_client: TestClient) -> None:
    """The page holds the sections of the install."""
    async with webserver_client.get("/") as resp:
        assert resp.status == 200
        body = await resp.text()

    for section in ("Server Status", "Clean Logs", "Bots", "Clients", "Users"):
        assert section in body
    # The map of a job is shown with the job it belongs to.
    assert "Maps" not in body
    assert 'id="map-viewer"' in body


@pytest.mark.usefixtures("clean_database")
async def test_the_clean_logs_can_be_filtered_by_robot(webserver_client: TestClient) -> None:
    """The jobs of one robot can be picked out."""
    bot_repo.add("sn_1234", "did_1234", "p95mgv", "res1", "eco-ng")
    bot_repo.add("sn_5678", "did_5678", "p95mgv", "res1", "eco-ng")
    for did in ("did_1234", "did_5678"):
        start = 1699297517
        clean_log = CleanLog(f"{did}@{start}@res9")
        clean_log.did = did
        clean_log.ts = start
        clean_log.type = "auto"
        clean_log_repo.add_or_update(clean_log)

    async with webserver_client.get("/clean_logs?did=did_5678") as resp:
        assert resp.status == 200
        body = await resp.text()

    # The job of the other robot is gone, the robot itself is still listed.
    assert "did_5678@1699297517@res9" in body
    assert "did_1234@1699297517@res9" not in body
    # The robot that is picked is the one that is shown.
    assert '<option value="did_5678" selected>' in body


@pytest.mark.usefixtures("clean_database")
async def test_the_clean_logs_show_every_robot_without_a_filter(webserver_client: TestClient) -> None:
    """Without a filter every job is shown."""
    bot_repo.add("sn_1234", "did_1234", "p95mgv", "res1", "eco-ng")
    bot_repo.add("sn_5678", "did_5678", "p95mgv", "res1", "eco-ng")
    for did in ("did_1234", "did_5678"):
        start = 1699297517
        clean_log = CleanLog(f"{did}@{start}@res9")
        clean_log.did = did
        clean_log.ts = start
        clean_log.type = "auto"
        clean_log_repo.add_or_update(clean_log)

    async with webserver_client.get("/clean_logs") as resp:
        assert resp.status == 200
        body = await resp.text()

    assert "did_5678@1699297517@res9" in body
    assert "did_1234@1699297517@res9" in body
    assert '<option value="" selected>' in body


@pytest.mark.usefixtures("clean_database")
@pytest.mark.parametrize(
    ("stop_reason", "label"),
    [
        (None, "Unknown"),
        (-2, "Unknown"),
        (-1, "Cleaning"),
        (1, "Finished"),
        (2, "Manually stopped"),
        (3, "Finished with warnings"),
        (99, "Unknown (99)"),
    ],
)
async def test_a_clean_log_shows_its_stop_reason(
    webserver_client: TestClient,
    stop_reason: int | None,
    label: str,
) -> None:
    """The stop reason is shown as text, with the stored value as its tooltip."""
    did = "did_1234"
    start = 1699297517
    clean_log = CleanLog(f"{did}@{start}@res9")
    clean_log.did = did
    clean_log.ts = start
    clean_log.type = "auto"
    clean_log.stop_reason = stop_reason
    clean_log_repo.add_or_update(clean_log)

    async with webserver_client.get("/clean_logs") as resp:
        assert resp.status == 200
        body = await resp.text()

    if stop_reason is None:
        assert f">{label}<" in body
    else:
        assert f'<td title="{stop_reason}">{label}</td>' in body


@pytest.mark.usefixtures("clean_database")
async def test_a_clean_log_shows_its_map(webserver_client: TestClient) -> None:
    """The map of a job is behind the menu of the job."""
    did = "did_1234"
    start = 1699297517
    clean_log = CleanLog(f"{did}@{start}@res9")
    clean_log.did = did
    clean_log.ts = start
    clean_log.type = "auto"
    clean_log_repo.add_or_update(clean_log)
    photo_repo.add(
        {
            "id": "1699297817000did_1234",
            "did": did,
            # The map was uploaded after the job started.
            "ts": 1699297817,
            "size": 10,
            "type": "robot",
            "mtype": "pic",
            "kind": "map",
            "image": photo_repo.encode_image(b"{}"),
        },
    )

    async with webserver_client.get("/clean_logs") as resp:
        assert resp.status == 200
        body = await resp.text()

    assert "Show map" in body
    # The map is only loaded when it is asked for.
    assert "/api/photo/download?id=1699297817000did_1234" in body
    assert "<img" not in body


@pytest.mark.usefixtures("clean_database")
async def test_a_clean_log_without_a_map_has_no_map(webserver_client: TestClient) -> None:
    """A job without a map has nothing to show."""
    did = "did_1234"
    start = 1699297517
    clean_log = CleanLog(f"{did}@{start}@res9")
    clean_log.did = did
    clean_log.ts = start
    clean_log.type = "auto"
    clean_log_repo.add_or_update(clean_log)

    async with webserver_client.get("/clean_logs") as resp:
        assert resp.status == 200
        body = await resp.text()

    assert "Show map" not in body


@pytest.mark.usefixtures("clean_database")
async def test_a_map_of_another_job_is_not_shown(webserver_client: TestClient) -> None:
    """The map of a job is the map that was uploaded after the job started."""
    did = "did_1234"
    start = 1699297517
    clean_log = CleanLog(f"{did}@{start}@res9")
    clean_log.did = did
    clean_log.ts = start
    clean_log.type = "auto"
    clean_log_repo.add_or_update(clean_log)
    photo_repo.add(
        {
            "id": "1000did_1234",
            "did": did,
            # The map was uploaded before the job started.
            "ts": 1000,
            "size": 10,
            "type": "robot",
            "mtype": "pic",
            "kind": "map",
            "image": photo_repo.encode_image(b"{}"),
        },
    )

    async with webserver_client.get("/clean_logs") as resp:
        assert resp.status == 200
        body = await resp.text()

    assert "Show map" not in body


@pytest.mark.usefixtures("clean_database")
async def test_the_actions_of_a_row_are_a_menu(webserver_client: TestClient) -> None:
    """The actions of a row hide behind a small menu."""
    bot_repo.add("sn_1234", "did_1234", "p95mgv", "res1", "eco-ng")
    bot_repo.set_nick("did_1234", "DEEBOT T10")

    async with webserver_client.get("/bots") as resp:
        assert resp.status == 200
        body = await resp.text()

    assert 'class="menu"' in body
    # The menu keeps its state when the table around it is replaced.
    assert "hx-preserve" in body
    # The menu holds the actions of the row.
    assert "renameEntity(this)" in body
    assert "removeEntity(this)" in body
    # The name of the robot is the value of the field of the rename.
    assert 'data-value="DEEBOT T10"' in body
    # The buttons of the row are gone, only the menu is left.
    assert "btn-outline-danger" not in body


async def test_favicon(webserver_client: TestClient) -> None:
    async with webserver_client.get("/favicon.ico") as resp:
        assert resp.status == 200
        content_type = resp.headers.get("Content-Type", "")
        assert content_type.startswith("image/")
        assert resp.content_length > 0
        # assert await resp.read()


async def test_favicon_missing(
    monkeypatch: pytest.MonkeyPatch,
    webserver_client: TestClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with patch("bumper.web.server") as mock_files:
        # Simulate Path that does NOT exist
        fake_path = Path("/tmp/nonexistent.ico")  # noqa: S108
        mock_files.return_value.joinpath.return_value = fake_path
        monkeypatch.setattr(Path, "exists", lambda _: False)

        async with webserver_client.get("/favicon.ico") as resp:
            assert resp.status == 500
            body = await resp.text()
            assert "Internal Server Error" in body
            assert "Favicon not found at" in caplog.text


@pytest.mark.usefixtures("clean_database")
async def test_set_user_nickname(webserver_client: TestClient) -> None:
    """The nickname is the display name the app shows for the member."""
    user_repo.add("uid_nick")

    async with webserver_client.get("/user/nickname/uid_nick?nickname=Kitchen%20robot") as resp:
        assert resp.status == 200
        body = await resp.json()

    assert body["status"] == "successfully set nickname for uid_nick"
    assert user_repo.get_by_id("uid_nick").nickname == "Kitchen robot"


@pytest.mark.usefixtures("clean_database")
async def test_set_user_nickname_for_an_unknown_user(webserver_client: TestClient) -> None:
    """An unknown user is not renamed."""
    async with webserver_client.get("/user/nickname/uid_nope?nickname=Kitchen%20robot") as resp:
        assert resp.status == 200
        body = await resp.json()

    assert "failed" in body["status"]


@pytest.mark.usefixtures("clean_database")
async def test_set_bot_nickname(webserver_client: TestClient) -> None:
    """The nickname is the display name the app shows for the robot."""
    bot_repo.add("sn_nick", "did_nick", "p95mgv", "res1", "eco-ng")

    async with webserver_client.get("/bot/nickname/did_nick?nickname=Test%20robot") as resp:
        assert resp.status == 200
        body = await resp.json()

    assert body["status"] == "successfully set nickname for did_nick"
    assert bot_repo.get("did_nick").nick == "Test robot"


async def test_the_bots_page_shows_the_firmware_version(webserver_client: TestClient) -> None:
    """The version of the firmware a robot runs is shown with the bot."""
    bot_repo.add("sn_1234", "did_1234", "p95mgv", "res1", "eco-ng")
    bot_repo.set_fw_ver("did_1234", "1.2.3")

    async with webserver_client.get("/bots") as resp:
        assert resp.status == 200
        body = await resp.text()

    assert "1.2.3" in body
    assert "Firmware" in body


async def test_the_bots_page_shows_no_version_when_the_robot_reported_none(webserver_client: TestClient) -> None:
    """A robot that did not report a version shows a dash."""
    bot_repo.add("sn_1234", "did_1234", "p95mgv", "res1", "eco-ng")

    async with webserver_client.get("/bots") as resp:
        assert resp.status == 200
        body = await resp.text()

    assert "Firmware" in body
