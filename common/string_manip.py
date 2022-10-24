#!/usr/bin/env python
"""Common string manipulation functions"""


def truncate_path_between(input_path: str, start_length=3, end_length=2) -> str:
    """Truncate long paths from the middle.

    /home/user/some/long/path/to/somewhere/far/away
    /home/user/some/.../far/away

    where `start_length` sets amount of portions on the left side of the dots
    and `end_length` vice versa on the right side."""

    parts = [x for x in input_path.split("/") if x != ""]
    if len(parts) < start_length + end_length:
        # nothing to do, already in parameters
        return input_path

    return "/".join(parts[:start_length]) + "/.../" + "/".join(parts[-end_length:])


def truncate_string(string: str, length=24, ending="...") -> str:
    """Truncate string with `ending`. `length` includes `ending`"""
    return string[: min(length, len(string)) - len(ending)] + ending
