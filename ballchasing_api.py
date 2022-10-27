from typing import IO, Any, Literal, Mapping, TypedDict

import requests

from common.config import Config
from common.printer import Printer

print = Printer.print


def health_check(s: requests.Session) -> bool:
    """Ping the ballchasing.com API.
    Returns:
        (bool): Healthy?"""

    # health check
    ping = s.get(f"{Config.api_url}/")
    healthy = ping.status_code == 200
    if healthy and Config.verbosity > 1:
        print("API health check OK")
    elif not healthy and Config.verbosity > 1:
        print(f"API health check failed: {ping.status_code}")

    return healthy


class BaseResult(TypedDict):
    result: Literal[
        "success", "duplicate", "fail"
    ]  # success: new upload, duplicate: already exists, fail: something is wrong
    id: str  # ballchasing.com replay id


class UploadResult(BaseResult):
    status_code: int  # HTTP status code
    json: dict  # response json


def upload_replay(
    s: requests.Session, file_: Mapping[str, IO], visibility: str = "private"
) -> UploadResult:
    """Upload a replay `file_` to ballchasing.com
    Returns:
        (UploadResult): Result of the upload attempt."""
    upload = s.post(Config.upload_url + "?visibility=" + visibility, files=file_)

    result: UploadResult = {
        "status_code": upload.status_code,
        "json": upload.json(),
        "id": "",
        "result": "fail",
    }

    # successful new upload
    if upload.status_code == 201:
        result["result"] = "success"
        result["id"] = result["json"]["id"]
        if Config.verbosity > 0:
            id_ = result["id"]
            print(f"Upload successful. Replay ID: {id_}")
    # existing duplicate found
    elif upload.status_code == 409:
        result["result"] = "duplicate"
        result["id"] = result["json"]["id"]
        if Config.verbosity > 0:
            id_ = result["id"]
            print(f"Duplicate replay found. Replay ID: {id_}")

    return result
