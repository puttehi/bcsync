import argparse
import datetime
import glob
import json
import os
import re
import struct
import sys
import time
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

import requests
from tabulate import tabulate

import ballchasing_api
from common.config import Config
from common.file_handlers import (append_to_file, find_files_endswith,
                                  overwrite_to_file,
                                  remove_duplicate_lines_from_file,
                                  write_rotated_log)
from common.printer import Printer

print = Printer.print
clear_lines = Printer.clear_lines
from common.string_manip import truncate_path_between, truncate_string
from replay import Replay, ReplayData
from runner import RunResult
from session import Session

__version__ = ""
with open("pyproject.toml", "r") as f:
    while not "[tool.poetry]" in f.readline():
        pass
    while l := f.readline():
        __version__ += l
        if l.startswith("\n") or l.startswith("["):
            break


SUCCESS, ERR, ERR_USAGE = 0, 1, 2


def read_args() -> Tuple[argparse.Namespace, int]:
    """Read command line arguments"""
    parser = argparse.ArgumentParser(
        epilog="Upload replays to ballchasing.com. Pass in either arg to auth."
    )
    parser.add_argument(
        "-c",
        "--check",
        help="Only print replay info",
        action="store_true",
    )
    parser.add_argument(
        "-e",
        "--env",
        help=".env file to read values from. Other arguments might overwrite the values from the file",
        default=None,
    )
    parser.add_argument(
        "-p",
        "--print_viewer_url",
        help="Print URL to ballchasing.com 3D replay viewer in session logs",
        action="store_true",
    )
    parser.add_argument(
        "-r",
        "--replay_path",
        help="Path to replay(s?) to upload",
        default=None,
    )
    parser.add_argument(
        "-t",
        "--token",
        help="ballchasing.com API token. Can also be passed as env API_TOKEN",
        default=None,
    )
    parser.add_argument(
        "-v", "--verbosity", action="count", default=0, help="Verbosity (-v, -vv, ..)"
    )
    parser.add_argument(
        "--version", action="store_true", help="Show application version"
    )
    parser.add_argument(
        "-w",
        "--watch",
        help="Watch for uploads every N seconds. Or use '1 s', '1 m' 1 h'",
        default=0,
    )

    args = parser.parse_args()
    if not args.version and args.env is None and args.token is None:
        print(
            "You must pass in --env or --token to authenticate with the ballchasing.com API: https://ballchasing.com/doc/api"
        )
        return args, ERR_USAGE

    return args, SUCCESS


def read_env(filepath: str | None) -> Dict[str, str]:
    """Read env file and return it as a dict.
    Args:
        filepath (str): environment file path
    Returns:
        env (Dict[str, str]): Environment as a Dict
    """
    env: Dict[str, str] = {}
    if filepath is None:
        return env

    with open(filepath, "r") as f:
        lines: List[str] = f.readlines()

    for l in lines:
        # KEY=VALUE
        delimiter_index = l.find("=")
        key = l[:delimiter_index]
        value = l[delimiter_index + 1 :].strip()
        env[key] = value

    return env


def print_replay_attributes(replay: Replay) -> str:
    """Print Replay object attributes and return the printed string."""
    printed = f"{'8<':-^20}\n"
    printed += str(vars(replay)) + "\n"
    printed += f"{'>8':-^20}\n"
    print(printed)

    return printed


def apply_overrides(suggested: Any, overrides: List[Any]) -> str:
    """Overrides `suggested` with values from `overrides` in order but skips values that are `None`.
    Example:
        `suggested`: "abc"
        `overrides`: [[], None, "123", {}]
        returns: {}
    Returns:
        (Any): Overriden `suggested`"""
    forced = suggested
    for o in overrides:
        if o is not None:
            forced = o

    return forced


def parse_watch(watch: str) -> int:
    """Parse `--watch` argument"""
    ws_count = watch.count(" ")
    w = 0
    if ws_count == 0:
        w = int(watch)
    elif ws_count == 1:
        s = watch.split(" ")
        num = int(s[0])
        sign = s[1]
        multi = 1
        if sign[0] == "m":
            multi = 60
        elif sign[0] == "h":
            multi = 3600
        w = num * multi
    else:
        raise ValueError(
            "Give --watch in form '0' (seconds) or '0 <m|h> (minutes, hours)'"
        )

    return w


def update_config(args: argparse.Namespace, env: dict[str, str]) -> None:
    """Update Config variables"""
    Config.set_verbosity(args.verbosity)
    Config.set_working_directory(os.path.dirname(__file__))
    Config.set_duplicates_file(
        os.path.join(Config.working_directory, "known_duplicates.db")
    )
    Config.set_watch(parse_watch(args.watch))
    Config.set_print_viewer_url(args.print_viewer_url)

    Config.set_api_token(
        apply_overrides(env["API_TOKEN"], [os.getenv("API_TOKEN", None), args.token])
    )
    Config.set_replay_path(
        apply_overrides(
            env["REPLAY_PATH"], [os.getenv("REPLAY_PATH", None), args.replay_path]
        ).strip()
    )

    if Config.verbosity > 0:
        print(f"config={str(vars(Config))}")
        print(f"{env=}")
        print(f"{args=}")


def main() -> int:
    """Entrypoint
    Returns:
        exit_code (int): Exit code (0 = success, 1 = error, 2 = usage, ...)
    """
    exit_code = 0
    args, exit_code = read_args()
    if exit_code != 0:
        return exit_code

    if args.version == True:
        print(f"* {'bcsync --version:':*^24}")
        print(f"{__version__.strip() + ' ':*^24}")
        print(f"* Suggestion: Try bcsync --help")
        return exit_code

    env: Dict[str, str] = read_env(args.env)
    update_config(args=args, env=env)

    # keep headers through session
    Session.session = requests.Session()
    Session.session.headers.update({"Authorization": Config.api_token})
    Session.run_results = []

    while True:
        clear_lines()
        if not ballchasing_api.health_check(Session.session):
            print(f"API health check failed. Retrying after 30 seconds.")
            time.sleep(30)
            continue

        # parse files to upload
        replays = [
            Replay(r)
            for r in find_files_endswith(dirpath=Config.replay_path, ending=".replay")
        ]
        _replays = replays  # cache for logging
        status_length = 36
        # upload
        run_result: RunResult = {
            "timestamp": datetime.datetime.now(),
            "replaydatas": [],
        }

        if args.check:
            for replay in replays:
                print_replay_attributes(replay)
                return SUCCESS

        Session.print_header()
        for replay in replays:
            rd = handle_replay(replay)
            if rd is not None:
                run_result["replaydatas"].append(rd)

        Session.update_session_statistics(replays=replays, run_result=run_result)
        clear_lines()
        if not args.check:
            Session.print_header()
            Session.print_body()

        # clean up dupe file of dupes in case we got any
        written_bytes = remove_duplicate_lines_from_file(
            filepath=Config.duplicates_file
        )
        if Config.verbosity > 1:
            print(
                f"Wrote {written_bytes} bytes to duplicates file {Config.duplicates_file}"
            )

        if Config.watch == 0:
            break

        time.sleep(int(Config.watch))

    return exit_code


def handle_replay(replay: Replay) -> Union[ReplayData, None]:
    """Handle a replay and return data if it made a request or None."""
    rd = upload_replay(replay)
    if rd is None:
        return None
    result = rd["result"]
    basename = rd["basename"]
    if result == "success" or result == "duplicate":
        # Success: So we know next time it is a duplicate
        # New duplicate: Well, it's a new duplicate
        append_to_file(filepath=Config.duplicates_file, text=basename)

    return rd


def upload_replay(replay: Replay, max_line_length=26) -> Union[ReplayData, None]:
    """Upload a Replay"""
    if Session.session is None:
        raise ValueError("No requests.Session set to Session.session")
    if Config.verbosity == 0:
        basename = replay.basename
        request_log = f"Out: {basename}"
        print(truncate_string(request_log, max_line_length), end="\r")
    rd: Optional[ReplayData] = replay.upload(Session.session)  # <-- slow
    if rd is None:
        # known duplicate, upload skipped
        return None

    if Config.verbosity > 0:
        result = rd["result"]
        basename = rd["basename"]
        response_log = f"In: {result} {basename}\n"
        print(truncate_string(response_log, max_line_length))

    return rd


def main_wrapper() -> int:
    """Capture exceptions from main to save session logs."""
    exit_code = 0
    try:
        exit_code = main()
        return exit_code
    except KeyboardInterrupt or Exception as e:
        Session.write_report_to_file()
        return exit_code


_replays: List[Replay] = []

if __name__ == "__main__":
    sys.exit(main_wrapper())
