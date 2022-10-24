import argparse
import datetime
import glob
import json
import os
import re
import struct
import sys
import time
from typing import Any, Dict, List, Literal, Tuple, Union

import requests
from tabulate import tabulate

import ballchasing_api
from common.config import Config
from common.file_handlers import (append_to_file, find_files_endswith,
                                  remove_duplicate_lines_from_file)
from common.string_manip import truncate_path_between, truncate_string
from replay import Replay

__version__ = ""
with open("pyproject.toml", "r") as f:
    while not "[tool.poetry]" in f.readline():
        pass
    while l := f.readline():
        __version__ += l
        if l.startswith("\n") or l.startswith("["):
            break


SUCCESS, ERR, ERR_USAGE = 0, 1, 2
SCRIPT_PATH = os.path.dirname(__file__)
SESSION_LOG_FILE = os.path.join(SCRIPT_PATH, "session.log")


def read_args() -> Tuple[argparse.Namespace, int]:
    """Read command line arguments"""
    parser = argparse.ArgumentParser(
        epilog="Upload replays to ballchasing.com. Pass in either arg to auth."
    )
    parser.add_argument(
        "-e",
        "--env",
        help=".env file to read values from. Other arguments might overwrite the values from the file",
        default=None,
    )
    parser.add_argument(
        "-t",
        "--token",
        help="ballchasing.com API token. Can also be passed as env API_TOKEN",
        default=None,
    )
    parser.add_argument(
        "-r",
        "--replay_path",
        help="Path to replay(s?) to upload",
        default=None,
    )
    parser.add_argument(
        "-c",
        "--check",
        help="Only print replay info",
        action="store_true",
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
        help="Watch for uploads every N milliseconds.",
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


def create_header_table(
    replays: List[Replay], replay_path: str
) -> Tuple[str, int, int, datetime.datetime]:
    """Create header table containing
    - Timestamp
    - Replay path
    - Upload/duplicate counts"""
    replay_path = truncate_path_between(replay_path)
    timestamp = datetime.datetime.now()
    success_count = len([r for r in replays if r.upload_result == "success"])
    old_duplicates_count = len(
        [r for r in replays if r.upload_result == "" and r.duplicate is True]
    )
    new_duplicates_count = len([r for r in replays if r.upload_result == "duplicate"])

    total_duplicates_count = old_duplicates_count + new_duplicates_count
    total_replay_count = total_duplicates_count + success_count
    return (
        tabulate(
            [
                ["Timestamp", timestamp],
                ["Replay path", replay_path],
                ["Total", total_duplicates_count + success_count],
                ["Successful", success_count],
                ["New duplicates", new_duplicates_count],
                ["Old duplicates", old_duplicates_count],
                ["Total duplicates", total_duplicates_count],
            ]
        ),
        success_count,
        new_duplicates_count,
        timestamp,
    )


def create_result_table(replays: List[Replay]) -> str:
    """TODO"""
    result_map = {
        "success": "New: ",
        "duplicate": "New duplicate: ",
    }
    return tabulate(
        [
            (
                truncate_string(replay.basename, 8 + 3),
                result_map.get(replay.upload_result) + replay.ballchasing_id,
            )
            for replay in replays
            if replay.upload_result != ""
        ]
    )


def build_table_strings(
    replays: List[Replay], replay_path: str
) -> Tuple[List[str], int, int, datetime.datetime]:
    """Print results tabulate and return the printed string."""
    if Config.verbosity > 1:
        print([replay.upload_json for replay in replays])

    header, successes, new, timestamp = create_header_table(replays, replay_path)
    tables = [header, create_result_table(replays)]
    return tables, successes, new, timestamp


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


def main() -> int:
    """Entrypoint
    Returns:
        exit_code (int): Exit code (0 = success, 1 = error, 2 = usage, ...)
    """
    global _session_log
    exit_code = 0
    args, exit_code = read_args()
    if exit_code != 0:
        return exit_code

    Config.set_verbosity(args.verbosity)

    if args.version == True:
        print(f"* {'bcsync --version:':*^24}")
        print(f"{__version__.strip() + ' ':*^24}")
        print(f"* Suggestion: Try bcsync --help")
        return exit_code

    env: Dict[str, str] = read_env(args.env)
    Config.set_api_token(
        apply_overrides(env["API_TOKEN"], [os.getenv("API_TOKEN", None), args.token])
    )
    Config.set_replay_path(
        apply_overrides(
            env["REPLAY_PATH"], [os.getenv("REPLAY_PATH", None), args.replay_path]
        ).strip()
    )
    Config.set_duplicates_file(os.path.join(SCRIPT_PATH, "known_duplicates.db"))

    _replay_path = Config.replay_path
    if Config.verbosity > 0:
        print(f"config={str(vars(Config))}")
        print(f"{env=}")
        print(f"{args=}")

    # keep headers through session
    s = requests.Session()
    s.headers.update({"Authorization": Config.api_token})

    Config.set_watch(args.watch)

    tick_rate = Config.watch
    while True:
        if not ballchasing_api.health_check(s):
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
        for replay in replays:
            if args.check:
                # --check so just print the attributes of the replays
                print_replay_attributes(replay)
                continue

            basename = replay.basename
            if Config.verbosity == 0:
                response_log = f"Out: {basename}"
                print(truncate_string(response_log, status_length), end="\r")
            result = replay.upload(s)
            if Config.verbosity > 0 and result != "old_duplicate":
                response_log = f"In: {result} {basename}\n"
                print(truncate_string(response_log, status_length))

            if result == "success" or result == "duplicate":
                # Success: So we know next time it is a duplicate
                # New duplicate: Well, it's a new duplicate
                append_to_file(Config.duplicates_file, replay.basename)

        if not args.check:
            (
                tables,
                success_count,
                new_duplicates_count,
                timestamp,
            ) = build_table_strings(
                replays=replays,
                replay_path=Config.replay_path,
            )
            print(tables[0])  # header for run

            if success_count > 0 or new_duplicates_count > 0:
                ts = f" {timestamp} "
                _session_log += f"{ts:-^36}\n"
                _session_log += f"{tables[1]}\n"

            print(_session_log)

        # clean up dupe file of dupes in case we got any
        written_bytes = remove_duplicate_lines_from_file(
            filepath=Config.duplicates_file
        )
        if Config.verbosity > 1:
            print(
                f"Wrote {written_bytes} bytes to duplicates file {Config.duplicates_file}"
            )

        if tick_rate == 0:
            break

        time.sleep(int(tick_rate) / 1000)

    return exit_code


def write_session_log() -> None:
    """Write session log to `SESSION_LOG_FILE`"""
    global _session_log
    next_index = 0
    log_file = SESSION_LOG_FILE
    log_basename = os.path.basename(log_file)
    log_dirglob = os.path.dirname(log_file) + "/session.log*"
    # print(log_file)
    # print(log_basename)
    # print(log_dirglob)
    for filepath in glob.iglob(log_dirglob, recursive=False):
        log_index = re.search(r"\d+", filepath)
        # print(log_index)
        if log_index is not None:
            s = log_index.span()
            idx = int(filepath[s[0] : s[1]])
            next_index = min(max(next_index, int(str(idx))), 10) + 1
            # print(next_index)
    if next_index == 0 and os.path.exists(log_file):
        next_index = 1
    if next_index > 0:
        log_file += str(next_index)
    # print(next_index)
    # print(log_file)
    with open(log_file, "w") as f:
        header, s, n, timestamp = create_header_table(_replays, _replay_path)
        session_report = header + "\n" + _session_log
        written_bytes = append_to_file(filepath=log_file, text=session_report)
        print(session_report)
        print(f"Wrote {written_bytes} bytes to {log_file}")


def main_wrapper() -> int:
    """Capture exceptions from main to save session logs."""
    exit_code = 0
    try:
        exit_code = main()
        return exit_code
    except KeyboardInterrupt or Exception as e:
        write_session_log()
        return exit_code


_session_log: str = ""
_replays: List[Replay] = []
_replay_path: str = ""

if __name__ == "__main__":
    sys.exit(main_wrapper())
