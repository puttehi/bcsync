#!/usr/bin/env python
"""File handling functions for bcsync"""
import glob
import os
from typing import List

from common.config import Config


def remove_duplicate_lines_from_file(filepath: str) -> int:
    """Clean up the file in `filepath` from duplicate lines.
    Returns:
        (int): Total bytes written back to `filepath`"""
    uniques = set()
    basename = os.path.basename(filepath)
    exists = os.path.exists(filepath)
    total_bytes_written = 0
    if not exists:
        if Config.verbosity > 0:
            print(f"No duplicates to clean as file does not exist: {filepath}")
        return total_bytes_written

    with open(filepath, "r") as f:
        lines = f.readlines()
        for l in lines:
            uniques.add(l)

    if Config.verbosity > 1:
        print(f"Cleaning up {basename}: {lines}")
    uniques_list = list(uniques)
    total_bytes_written += overwrite_to_file(filepath, uniques_list[0])
    for u in uniques_list[1:]:
        total_bytes_written += append_to_file(filepath, u)
    if Config.verbosity > 1:
        print(
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


def overwrite_to_file(filepath: str, text: str) -> int:
    """Overwrite file content of `filepath` with `text`.
    Create the file if it doesn't exist.
    Returns:
        (int): Total bytes written to `filepath`"""
    total_bytes = 0
    with open(filepath, "w") as f:
        total_bytes = f.write(text.rstrip() + "\n")

    return total_bytes
