import argparse
import datetime
import glob
import json
import os
import struct
import sys
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

    @staticmethod
    def read_known_duplicates() -> List[str]:
        try:
            with open("known_duplicates.db", "r") as f:
                return [
                    l.strip() for l in f.readlines() if l != "\n"
                ]  # strip newlines from the raw read and disregard line breaks
        except FileNotFoundError as e:
            return []

    known_duplicates = read_known_duplicates()
    upload_url_base = "https://ballchasing.com/api/v2/upload"


def read_replay(filepath: str) -> Replay:
    """TODO"""
    return Replay(filepath)


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
    if args.verbosity > 0:
        print(env)
        print(args)

    if env.get("API_TOKEN", None) is None:
        env["API_TOKEN"] = os.getenv("API_TOKEN", "")
    if args.token:
        env["API_TOKEN"] = args.token
    if env.get("REPLAY_PATH", None) is None:
        env["REPLAY_PATH"] = os.getenv("REPLAY_PATH", "")
    if args.replay_path:
        env["REPLAY_PATH"] = args.replay_path

    should_upload = not args.check

    # keep headers through session
    s = requests.Session()
    s.headers.update({"Authorization": env["API_TOKEN"].strip()})

    # health check
    ping = s.get("https://ballchasing.com/api/")
    assert (
        ping.status_code == 200
    ), f"API health check did not return 200: {ping.status_code}"
    if args.verbosity > 1:
        print("API health check OK")

    # parse files to upload
    replays = []
    # determine if path is a folder or a file
    if env["REPLAY_PATH"].endswith(".replay"):
        replays.append(read_replay(env["REPLAY_PATH"]))
    else:
        # root_dir needs a trailing slash (i.e. /root/dir/)
        for filepath in glob.iglob(env["REPLAY_PATH"] + "**/*.replay", recursive=True):
            replays.append(read_replay(filepath))

    # upload
    for replay in replays:
        if not should_upload:
            # --check so just print the attributes of the replays
            print(f"{'8<':-^20}")
            print(vars(replay))
            print(f"{'>8':-^20}")
            continue

        result = replay.upload(s, args.verbosity)
        if result == "success" or result == "new_duplicate":
            # Success: So we know next time it is a duplicate
            # New duplicate: Well, it's a new duplicate
            with open("known_duplicates.db", "a") as f:
                f.write(replay.basename + "\n")

    if should_upload:
        if args.verbosity > 1:
            print([replay.upload_json for replay in replays])
        replay_path = truncate_path_between(env["REPLAY_PATH"])
        timestamp = datetime.datetime.now()
        success_count = 0
        old_duplicates_count = 0
        new_duplicates_count = 0
        for replay in replays:
            if replay.upload_result == "":
                if replay.duplicate is True:
                    old_duplicates_count += 1
            else:
                if replay.duplicate is True:
                    new_duplicates_count += 1
                else:
                    success_count += 1
        total_duplicates_count = old_duplicates_count + new_duplicates_count
        total_replay_count = total_duplicates_count + success_count

        # TODO: Report ID and path of new uploads and duplicates
        print(
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
            )
        )
        result_map = {
            "success": "New: ",
            "duplicate": "New duplicate: ",
        }

        print(
            tabulate(
                [
                    (
                        truncate_string(replay.basename, 8 + 3),
                        result_map.get(replay.upload_result) + replay.ballchasing_id,
                    )
                    for replay in replays
                    if replay.upload_result != ""
                ]
            )
        )
    # clean up dupe file of dupes in case we got any
    duplicates = set()
    with open("known_duplicates.db", "r") as f:
        lines = f.readlines()
        for l in lines:
            duplicates.add(l)
        if args.verbosity > 1:
            print(f"Cleaning up known_duplicates.db: {lines}")
    with open("known_duplicates.db", "w") as f:
        for d in duplicates:
            f.write(d + "\n")
        if args.verbosity > 1:
            print(f"Wrote duplicates to known_duplicates.db: {str(duplicates)}")

    return exit_code


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


if __name__ == "__main__":
    sys.exit(main())
