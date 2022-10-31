#!/usr/bin/env python
"""Common string manipulation functions"""
import textwrap
from math import floor
from typing import Union


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


def wrap_and_truncate_string(string: str, ending="...", lines=0, columns=0) -> str:
    """Wrap string to `lines` fitting in `columns`, truncating the rest with `ending`"""
    wrapped = textwrap.wrap(string, columns)[:lines]
    wrapped[-1] = truncate_string(string=wrapped[-1], length=columns)
    return "\n".join(wrapped)


def center_pad_string(
    string: str, line_length: int, ws_pad_count=4, pad_char=" "
) -> str:
    """Pad `string` with whitespaces so it is centered on a line of length `line_length`.
    If `pad_char` is given, `ws_pad_count` can be used to adjust the amount of whitespace
    and `pad_char`.
    Default count 4 and char `"."` on 12 length line with string "abcd":
        "abcd" input string
        "    abcd    " 12 line length
        "..  abcd  .." 12 line length and char '.' with default pad count 4"""
    ws_padding = len(string) + ws_pad_count
    ws_padded = "{s:{c}^{n}}".format(s=string, c=" ", n=ws_padding)

    char_padded = "{s:{c}^{n}}\n".format(s=ws_padded, c=pad_char, n=line_length)

    return char_padded


def seconds_to_mm_ss(seconds: Union[str, int]) -> str:
    """Convert `seconds` to MM:SS"""
    int(seconds)
    minutes = floor(seconds / 60)
    remainder = seconds - (minutes * 60)
    return f"{str(minutes).rjust(2, '0')}:{str(remainder).rjust(2, '0')}"
