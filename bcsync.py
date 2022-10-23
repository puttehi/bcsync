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


def read_replay(filepath: str) -> Replay:
    """TODO"""
    return Replay(filepath)


def upload_replay(
    s: requests.Session, replay_path: str, verbosity: int = 0
) -> Tuple[Union[Literal["success"], Literal["duplicate"]], Dict[str, Any]]:
    """TODO"""
    visibility = "private"  # public
    upload_url = f"https://ballchasing.com/api/v2/upload?visibility={visibility}"
    file_ = {"file": open(replay_path, "rb")}

    upload = s.post(upload_url, files=file_)

    if upload.status_code == 201:
        # replay successfully created, return it's id
        j = upload.json()
        id = j["id"]
        if verbosity > 0:
            print(f"Upload successful. Replay ID: {id}")
        return "success", j
    elif upload.status_code == 409:  # duplicate replay
        # you have the choice: either raise an error, or return the existing replay id
        j = upload.json()
        id = j["id"]
        if verbosity > 0:
            print(f"Duplicate replay found. Replay ID: {id}")
        return "duplicate", j
    else:
        # raise an error for other status codes (50x, ...)
        raise Exception(json.dumps(upload.json()))


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
    results: Dict[str, List[Dict[str, Any]]] = {"duplicate": [], "success": []}
    new_duplicates_count = 0
    old_duplicates_count = 0
    for replay in replays:
        if should_upload:
            if replay.duplicate:
                # old duplicate
                if args.verbosity > 0:
                    print(f"Skipping known duplicate: {replay.basename}")
                key, value = "duplicate", replay
                results[key].append(value)
                old_duplicates_count += 1
                continue
            key, value = upload_replay(s, replay.path, args.verbosity)
            results[key].append(value)
            if key == "duplicate":
                # new duplicate
                with open("known_duplicates.db", "a") as f:
                    f.write(replay.basename + "\n")
                new_duplicates_count += 1
        else:
            print(f"{'8<':-^20}")
            print(vars(replay))
            print(f"{'>8':-^20}")

    if should_upload:
        if args.verbosity > 0:
            print(results)
        success_count = len(results.get("success", []))
        total_duplicates_count = len(results.get("duplicate", []))
        replay_path = path_smart_truncate(env["REPLAY_PATH"])
        timestamp = datetime.datetime.now()
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

    # clean up dupe file of dupes in case we got any
    duplicates = set()
    with open("known_duplicates.db", "r") as f:
        lines = f.readlines()
        for l in lines:
            duplicates.add(l)
        if args.verbosity > 0:
            print(f"Cleaning up known_duplicates.db: {lines}")
    with open("known_duplicates.db", "w") as f:
        for d in duplicates:
            f.write(d + "\n")
        if args.verbosity > 0:
            print(f"Wrote duplicates to known_duplicates.db: {str(duplicates)}")

    return exit_code


def path_smart_truncate(input_path: str, start_length=3, end_length=2) -> str:
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


if __name__ == "__main__":
    sys.exit(main())
