#!/usr/bin/env python
"""File handling functions for bcsync"""
import glob
import os
from typing import Any, Callable, List, Optional

from config import Config
from gui import GUI


def remove_duplicate_lines_from_file(filepath: str, gui: Optional[GUI] = None) -> int:
    """Clean up the file in `filepath` from duplicate lines.
    Returns:
        (int): Total bytes written back to `filepath`"""
    uniques = set()
    basename = os.path.basename(filepath)
    exists = os.path.exists(filepath)
    total_bytes_written = 0
    if not exists:
        if Config.verbosity > 0 and gui is not None:
            gui.print(f"No duplicates to clean as file does not exist: {filepath}")
        return total_bytes_written

    lines = read_file_lines(filepath)
    for l in lines:
        uniques.add(l)

    if Config.verbosity > 1 and gui is not None:
        gui.print(f"Cleaning up {basename}: {lines}")
    uniques_list = list(uniques)
    total_bytes_written += overwrite_to_file(filepath, uniques_list[0])
    for u in uniques_list[1:]:
        total_bytes_written += append_to_file(filepath, u)
    if Config.verbosity > 1 and gui is not None:
        gui.print(
            f"Wrote {len(uniques_list)} unique rows ({total_bytes_written} bytes) to {basename}: {str(uniques_list)}"
        )

    return total_bytes_written


def find_files_endswith(dirpath: str, ending: str, recurse=True) -> List[str]:
    """Find files from `dirpath` ending in `ending`.
    `dirpath` can be a file ending in `ending` or a
    folder to be walked recursively if `recurse`.
    Returns:
        (List[str]): List of found files ending in `ending` or [] if none were found."""
    found_files = []
    if dirpath.endswith(ending):
        found_files.append(dirpath)
    else:
        # root_dir needs a trailing slash (i.e. /root/dir/)
        found_files = [
            f for f in glob.iglob(dirpath + f"**/*{ending}", recursive=recurse)
        ]

    return found_files


def ensure_dir_exists(func: Callable[..., Any]):
    """Create directory of `kwargs.filepath` (or arg 0) if it doesn't exist"""

    def wrapper(*args, **kwargs):
        filepath = kwargs.get("filepath", None)
        if filepath is None:
            filepath = args[0]

        dirpath = os.path.dirname(filepath)
        if not os.path.exists(dirpath):
            os.makedirs(name=dirpath, exist_ok=True)

        return func(*args, **kwargs)

    return wrapper


@ensure_dir_exists
def append_to_file(filepath: str, text: str) -> int:
    """Append `text` to `filepath`.
    Create the file if it doesn't exist.
    Returns:
        (int): Total bytes written to `filepath`"""
    total_bytes = 0
    try:
        with open(filepath, "a") as f:
            total_bytes = f.write(text.rstrip() + "\n")
    except FileNotFoundError as e:
        total_bytes = overwrite_to_file(filepath=filepath, text=text)

    return total_bytes


@ensure_dir_exists
def overwrite_to_file(filepath: str, text: str) -> int:
    """Overwrite file content of `filepath` with `text`.
    Create the file if it doesn't exist.
    Returns:
        (int): Total bytes written to `filepath`"""
    total_bytes = 0
    with open(filepath, "w") as f:
        total_bytes = f.write(text.rstrip() + "\n")

    return total_bytes


def read_file_lines(filepath: str) -> List[str]:
    """Read contents of `filepath` as a list of strings
    or empty list if no file exists."""
    lines: List[str] = []

    try:
        with open(filepath, "r") as f:
            lines = f.readlines()
    except FileNotFoundError as e:
        pass

    return lines


def read_rotate_file(identifier: str) -> int:
    """Read `identifier`.rotate for the current log index"""
    rotate_file = os.path.join(Config.working_directory, "log", f"{identifier}.rotate")
    with open(rotate_file, "r") as f:
        return int(f.readline())


def write_rotate_file(identifier: str, index: int) -> int:
    """Write current log index to `identifier`.rotate.
    Returns:
        (int): Total bytes written"""
    rotate_file = os.path.join(Config.working_directory, "log", f"{identifier}.rotate")
    return overwrite_to_file(rotate_file, str(index))


def get_next_rotate_index(identifier: str) -> int:
    """Get next log index using `identifier`.rotate
    or 0 if it doesn't exist."""
    try:
        return read_rotate_file(identifier=identifier) + 1
    except FileNotFoundError as e:
        return 0


def write_rotated_log(identifier: str, text: str, gui: Optional[GUI]) -> None:
    """Write session log to `identifier`.logN
    where N is the next log index determined
    from `identifier`.rotate storing the current
    log index N. First log is written without a
    suffix N."""

    next_index = get_next_rotate_index(identifier=identifier)
    if next_index > Config.max_session_logfiles:
        next_index = 0

    log_file = os.path.join(Config.working_directory, "log", f"{identifier}.log")
    if next_index > 0:
        log_file += str(next_index)

    written_bytes = overwrite_to_file(filepath=log_file, text=text)
    if gui is not None:
        gui.print(text)
        gui.print(f"Wrote {written_bytes} bytes to {log_file}")

    write_rotate_file(identifier=identifier, index=next_index)
