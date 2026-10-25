"""The files that the server serves from a directory.

Some endpoints serve a file that is not part of the distribution: the voice
files the robot downloads, the CodePush packages the app downloads. The name
of the file comes from the request, so it must not be able to name a file
outside of the directory it belongs to.
"""

from pathlib import Path


def file_in_dir(directory: Path, name: str) -> Path | None:
    """Return the file with this name in the directory, if the directory has it.

    The name comes from the request, so it is checked twice:

    - it has to be a plain name, without a path separator and without a
      reference to a directory,
    - and the file it names has to be inside the directory, after the links
      of the path are resolved.

    The second check is the one that counts: a name that walks out of the
    directory, or a link inside it that points out of it, is not served.
    """
    if not name or name in {".", ".."}:
        return None
    if any(part in name for part in ("/", "\\", "\x00")):
        return None

    try:
        resolved = (directory / name).resolve(strict=True)
        root = directory.resolve(strict=True)
    except OSError:
        return None

    if not resolved.is_relative_to(root):
        return None
    if not resolved.is_file():
        return None
    return resolved
