import argparse
import datetime
import glob
import json
import os
import struct
import sys
import time
from typing import Any, Dict, List, Literal, Tuple, Union

import requests
from tabulate import tabulate

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
DUPLICATES_FILE = os.path.join(SCRIPT_PATH, "known_duplicates.db")


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


class Replay:
    def __init__(self, path=""):
        self.read_known_duplicates()
        self.path = path
        self.basename = os.path.basename(self.path)
        self.duplicate = self.basename in self.known_duplicates
        self.visibility = "private"
        self.ballchasing_id = ""
        self.upload_result = ""
        self.upload_json = {}

    def upload(
        self, session: requests.Session, verbosity: int = 0
    ) -> Union[Literal["success"], Literal["old_duplicate"], Literal["new_duplicate"]]:
        """Upload the replay to ballchasing.com.
        Returns:
            "duplicate": if previously uploaded
            "success": if a new upload was successful
        Raises:
            Exception: When upload was not successful or a duplicate"""
        if self.duplicate:
            if verbosity > 0:
                print(f"Skipping known duplicate: {self.basename}")
            return "old_duplicate"

        file_ = {"file": open(self.path, "rb")}

        upload = session.post(
            self.upload_url_base + "?visibility=" + self.visibility, files=file_
        )

        if upload.status_code == 201:
            # replay successfully created, return it's id
            self.upload_json = upload.json()
            id = self.upload_json["id"]
            self.ballchasing_id = id
            self.upload_result = "success"
            if verbosity > 0:
                print(f"Upload successful. Replay ID: {id}")
            return "success"
        elif upload.status_code == 409:  # duplicate replay
            # you have the choice: either raise an error, or return the existing replay id
            self.upload_json = upload.json()
            id = self.upload_json["id"]
            self.ballchasing_id = id
            self.upload_result = "duplicate"
            if verbosity > 0:
                print(f"Duplicate replay found. Replay ID: {id}")
            return "new_duplicate"
        else:
            # raise an error for other status codes (50x, ...)
            raise Exception(json.dumps(upload.json()))

    @classmethod
    def read_known_duplicates(cls) -> List[str]:
        try:
            with open(DUPLICATES_FILE, "r") as f:
                duplicates = [
                    l.strip() for l in f.readlines() if l != "\n"
                ]  # strip newlines from the raw read and disregard line breaks
                cls.known_duplicates = duplicates
                return duplicates
        except FileNotFoundError as e:
            return []

    known_duplicates: List[str] = []
    upload_url_base = "https://ballchasing.com/api/v2/upload"


def read_replay(filepath: str) -> Replay:
    """TODO"""
    return Replay(filepath)


def print_table(replays: List[Replay], replay_path: str, verbosity=0) -> str:
    """Print results tabulate and return the printed string."""
    if verbosity > 1:
        print([replay.upload_json for replay in replays])
    replay_path = truncate_path_between(replay_path)
    timestamp = datetime.datetime.now()
    success_count = len([r for r in replays if r.upload_result == "success"])
    old_duplicates_count = len(
        [r for r in replays if r.upload_result == "" and r.duplicate is True]
    )
    new_duplicates_count = len([r for r in replays if r.upload_result == "duplicate"])

    total_duplicates_count = old_duplicates_count + new_duplicates_count
    total_replay_count = total_duplicates_count + success_count

    # TODO: Report ID and path of new uploads and duplicates
    result_map = {
        "success": "New: ",
        "duplicate": "New duplicate: ",
    }
    tables = [
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
        tabulate(
            [
                (
                    truncate_string(replay.basename, 8 + 3),
                    result_map.get(replay.upload_result) + replay.ballchasing_id,
                )
                for replay in replays
                if replay.upload_result != ""
            ]
        ),
    ]
    printed = "\n".join(tables)
    print(printed)
    return printed


def clean_duplicates_file(verbosity=0) -> None:
    """Clean up `DUPLICATES_FILE` from duplicate entries."""
    duplicates = set()
    with open(DUPLICATES_FILE, "r") as f:
        lines = f.readlines()
        for l in lines:
            duplicates.add(l)
        if verbosity > 1:
            print(f"Cleaning up known_duplicates.db: {lines}")
    with open(DUPLICATES_FILE, "w") as f:
        for d in duplicates:
            f.write(d.rstrip() + "\n")
        if verbosity > 1:
            print(f"Wrote duplicates to known_duplicates.db: {str(duplicates)}")


def print_replay_attributes(replay: Replay) -> str:
    """Print Replay object attributes and return the printed string."""
    printed = f"{'8<':-^20}\n"
    printed += str(vars(replay)) + "\n"
    printed += f"{'>8':-^20}\n"
    print(printed)

    return printed


def parse_replays(replay_path: str, recurse=True) -> List[Replay]:
    """Read replays from `replay_path` to a list of Replays.
    `replay_path` can be a replay file ending in .replay or
    a folder to be walked recursively (try `recurse`)."""
    replays = []
    # determine if path is a folder or a file
    if replay_path.endswith(".replay"):
        replays.append(read_replay(replay_path))
    else:
        # root_dir needs a trailing slash (i.e. /root/dir/)
        for filepath in glob.iglob(replay_path + "**/*.replay", recursive=recurse):
            replays.append(read_replay(filepath))

    return replays


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


def truncate_string(string: str, length=24) -> str:
    """Truncate string with dots. `length` includes dots."""
    end = "..."
    return string[: min(length, len(string)) - len(end)] + end


def confirm_env(
    env: Dict[str, str], opts: List[Dict[str, str]], verbosity=0
) -> Dict[str, str]:
    confirmed = env.copy()
    for o in opts:
        if confirmed.get(o["key"], None) is None:
            confirmed[o["key"]] = os.getenv(o["key"], "")
        if o["arg"]:
            confirmed[o["key"]] = o["arg"]
    if verbosity > 1:
        print(confirmed)
    return confirmed


def append_to_file(filepath: str, text: str) -> None:
    """Append `text` to `filepath`.
    Create the file if it doesn't exist."""
    try:
        with open(filepath, "a") as f:
            f.write(text.rstrip() + "\n")
    except FileNotFoundError as e:
        with open(filepath, "w") as f:
            f.write(text.rstrip() + "\n")

    return


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
    env = confirm_env(
        env=env,
        opts=[
            {"key": "API_TOKEN", "arg": args.token},
            {"key": "REPLAY_PATH", "arg": args.replay_path},
        ],
        verbosity=args.verbosity,
    )
    if args.verbosity > 0:
        print(env)
        print(args)

    # keep headers through session
    s = requests.Session()
    s.headers.update({"Authorization": env["API_TOKEN"].strip()})

    tick_rate = args.watch
    while True:
        # health check
        ping = s.get("https://ballchasing.com/api/")
        assert (
            ping.status_code == 200
        ), f"API health check did not return 200: {ping.status_code}"
        if args.verbosity > 1:
            print("API health check OK")

        # parse files to upload
        replays = parse_replays(env["REPLAY_PATH"])

        # upload
        for replay in replays:
            if args.check:
                # --check so just print the attributes of the replays
                print_replay_attributes(replay)
                continue

            result = replay.upload(s, args.verbosity)
            if result == "success" or result == "new_duplicate":
                # Success: So we know next time it is a duplicate
                # New duplicate: Well, it's a new duplicate
                append_to_file(DUPLICATES_FILE, replay.basename)

        if not args.check:
            run_log = print_table(
                replays=replays,
                replay_path=env["REPLAY_PATH"],
                verbosity=args.verbosity,
            )

        # clean up dupe file of dupes in case we got any
        clean_duplicates_file(verbosity=args.verbosity)

        if tick_rate == 0:
            break

        time.sleep(int(tick_rate) / 1000)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
