"""The files the server serves from a directory."""

from pathlib import Path

from bumper.web.utils.files import file_in_dir


def test_the_file_of_the_directory_is_served(tmp_path: Path) -> None:
    """A file of the directory is found by its name."""
    (tmp_path / "voice-id").write_bytes(b"voice")

    assert file_in_dir(tmp_path, "voice-id") == (tmp_path / "voice-id").resolve()


def test_a_name_that_is_not_a_file_of_the_directory_is_not_served(tmp_path: Path) -> None:
    """The name has to be the name of a file that is there."""
    (tmp_path / "voice-id").write_bytes(b"voice")

    assert file_in_dir(tmp_path, "other-id") is None
    assert file_in_dir(tmp_path, "") is None
    assert file_in_dir(tmp_path, ".") is None
    assert file_in_dir(tmp_path, "..") is None


def test_a_name_that_walks_out_of_the_directory_is_not_served(tmp_path: Path) -> None:
    """A name with a path in it never leaves the directory."""
    (tmp_path.parent / "secret.txt").write_text("the secret of the user")

    assert file_in_dir(tmp_path, "../secret.txt") is None
    assert file_in_dir(tmp_path, "..%2Fsecret.txt") is None
    assert file_in_dir(tmp_path, "sub/../secret.txt") is None
    assert file_in_dir(tmp_path, "/etc/passwd") is None
    assert file_in_dir(tmp_path, "sub\\secret.txt") is None
    assert file_in_dir(tmp_path, "secret.txt\x00") is None


def test_a_link_that_points_out_of_the_directory_is_not_served(tmp_path: Path) -> None:
    """A link inside the directory cannot be used to serve another file."""
    secret = tmp_path.parent / "secret.txt"
    secret.write_text("the secret of the user")
    (tmp_path / "link").symlink_to(secret)

    assert file_in_dir(tmp_path, "link") is None


def test_a_directory_is_not_a_file(tmp_path: Path) -> None:
    """Only files are served."""
    (tmp_path / "sub").mkdir()

    assert file_in_dir(tmp_path, "sub") is None
