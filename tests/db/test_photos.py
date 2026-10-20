"""Tests for bumper/db/photos.py"""

import pytest

from bumper.db import photo_repo


def _photo(did: str, ts: int, photo_id: str = "") -> dict[str, object]:
    """Build a photo record."""
    return {
        "id": photo_id or f"{ts}{did}",
        "did": did,
        "ts": ts,
        "size": 10,
        "bindEvt": "cruise",
        "bindID": "",
        "type": "robot",
        "mtype": "pic",
        "image": photo_repo.encode_image(b"jpeg-bytes"),
    }


@pytest.mark.usefixtures("clean_database")
def test_add_and_get_by_photo_id() -> None:
    """A stored photo is found by its id."""
    photo_repo.add(_photo("did_a", 1000, "id_a"))

    record = photo_repo.get_by_photo_id("id_a")

    assert record is not None
    assert record["did"] == "did_a"


@pytest.mark.usefixtures("clean_database")
def test_get_unknown_photo_id_returns_none() -> None:
    """An unknown id has no record."""
    assert photo_repo.get_by_photo_id("nope") is None


@pytest.mark.usefixtures("clean_database")
def test_list_by_did_returns_only_that_device() -> None:
    """A device filter excludes the photos of the other devices."""
    photo_repo.add(_photo("did_a", 1000))
    photo_repo.add(_photo("did_b", 2000))

    records = photo_repo.list_by_did("did_a")

    assert [record["did"] for record in records] == ["did_a"]


@pytest.mark.usefixtures("clean_database")
def test_list_without_did_returns_every_device() -> None:
    """Without a device the photos of every robot are listed."""
    photo_repo.add(_photo("did_a", 1000))
    photo_repo.add(_photo("did_b", 2000))

    records = photo_repo.list_by_did(None)

    assert {record["did"] for record in records} == {"did_a", "did_b"}


@pytest.mark.usefixtures("clean_database")
def test_list_is_newest_first() -> None:
    """The newest photo comes first."""
    photo_repo.add(_photo("did_a", 1000))
    photo_repo.add(_photo("did_a", 3000))
    photo_repo.add(_photo("did_a", 2000))

    records = photo_repo.list_by_did("did_a")

    assert [record["ts"] for record in records] == [3000, 2000, 1000]


@pytest.mark.usefixtures("clean_database")
def test_list_honours_the_limit() -> None:
    """The limit caps the number of returned photos."""
    for ts in range(1000, 1005):
        photo_repo.add(_photo("did_a", ts))

    assert len(photo_repo.list_by_did("did_a", limit=2)) == 2


@pytest.mark.usefixtures("clean_database")
def test_list_before_skips_newer_photos() -> None:
    """`before` pages backwards through the history."""
    for ts in (1000, 2000, 3000):
        photo_repo.add(_photo("did_a", ts))

    records = photo_repo.list_by_did("did_a", before=3000)

    assert [record["ts"] for record in records] == [2000, 1000]


@pytest.mark.usefixtures("clean_database")
def test_prune_keeps_the_newest() -> None:
    """Pruning drops the oldest photos of a device."""
    for ts in (1000, 2000, 3000):
        photo_repo.add(_photo("did_a", ts))

    photo_repo.prune("did_a", 2)

    assert [record["ts"] for record in photo_repo.list_by_did("did_a")] == [3000, 2000]


@pytest.mark.usefixtures("clean_database")
def test_prune_leaves_other_devices_alone() -> None:
    """Pruning one device does not touch the photos of another."""
    photo_repo.add(_photo("did_a", 1000))
    photo_repo.add(_photo("did_b", 2000))

    photo_repo.prune("did_a", 0)

    assert photo_repo.list_by_did("did_a") == []
    assert len(photo_repo.list_by_did("did_b")) == 1


@pytest.mark.usefixtures("clean_database")
def test_remove_all() -> None:
    """Every photo can be dropped at once."""
    photo_repo.add(_photo("did_a", 1000))

    photo_repo.remove_all()

    assert photo_repo.list_all() == []


@pytest.mark.usefixtures("clean_database")
def test_image_round_trip() -> None:
    """A stored image decodes back to the bytes that went in."""
    assert photo_repo.decode_image(photo_repo.encode_image(b"jpeg-bytes")) == b"jpeg-bytes"


@pytest.mark.usefixtures("clean_database")
def test_the_time_of_a_map_is_scaled_up() -> None:
    """The robot sends the time of a map in seconds."""
    photo_repo.add(_photo("did_a", 1792439780))

    records = photo_repo.list_by_did("did_a")

    assert records[0]["ts"] == 1792439780000


@pytest.mark.usefixtures("clean_database")
def test_the_time_of_a_picture_is_kept() -> None:
    """The robot sends the time of a picture in milliseconds."""
    photo_repo.add(_photo("did_a", 1746022105000))

    records = photo_repo.list_by_did("did_a")

    assert records[0]["ts"] == 1746022105000


@pytest.mark.usefixtures("clean_database")
def test_the_stored_time_is_not_changed() -> None:
    """The time in the database is left as the robot sent it."""
    photo_repo.add(_photo("did_a", 1792439780))

    photo_repo.list_by_did("did_a")

    assert photo_repo.list_all()[0]["ts"] == 1792439780


@pytest.mark.usefixtures("clean_database")
def test_photos_of_both_kinds_are_ordered_by_their_time() -> None:
    """A map and a picture are ordered by the time they were made."""
    photo_repo.add(_photo("did_a", 1792439780))
    photo_repo.add(_photo("did_a", 1746022105000))

    records = photo_repo.list_by_did("did_a")

    assert [record["ts"] for record in records] == [1792439780000, 1746022105000]
