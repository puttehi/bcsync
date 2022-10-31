from typing import IO, Any, Dict, Literal, Mapping, TypedDict, Union

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


# 201: success
class UploadSuccessResponse(TypedDict):
    id: str  # replay id
    location: str  # replay url


# 409: duplicate
class UploadDuplicateResponse(TypedDict):
    id: str  # replay id
    location: str  # replay url
    error: Literal["duplicate replay"]
    chat: Dict[str, str]  # random chat, no idea some bc api thing


# 400: your fault, 500: api fault
class UploadErrorResponse(TypedDict):
    error: str


class BaseResult(TypedDict):
    result: Literal[
        "success", "duplicate", "fail"
    ]  # success: new upload, duplicate: already exists, fail: something is wrong
    id: str  # ballchasing.com replay id


class UploadResult(BaseResult):
    status_code: int  # HTTP status code
    json: Union[
        UploadSuccessResponse, UploadDuplicateResponse, UploadErrorResponse
    ]  # response json


def upload_replay(
    s: requests.Session, file_: Mapping[str, IO], visibility: str = "private"
) -> UploadResult:
    """Upload a replay `file_` to ballchasing.com
    Returns:
        (UploadResult): Result of the upload attempt."""
    upload = s.post(Config.upload_url + "?visibility=" + visibility, files=file_)

    result: UploadResult = {
        "status_code": upload.status_code,
        "json": {
            "error": "Something was not handled and result passed through unmutated"
        },
        "id": "",
        "result": "fail",
    }

    # successful new upload
    if upload.status_code == 201:
        js: UploadSuccessResponse = upload.json()
        result["json"] = js
        result["result"] = "success"
        result["id"] = js["id"]
        if Config.verbosity > 0:
            id_ = result["id"]
            print(f"Upload successful. Replay ID: {id_}")
    # existing duplicate found
    elif upload.status_code == 409:
        jd: UploadDuplicateResponse = upload.json()
        result["json"] = jd
        result["result"] = "duplicate"
        result["id"] = jd["id"]
        if Config.verbosity > 0:
            id_ = result["id"]
            print(f"Duplicate replay found. Replay ID: {id_}")

    return result


class UploaderData(TypedDict):
    avatar: str  # url
    name: str
    profile_url: str


class BaseReplayResult(TypedDict):
    status: Union[
        Literal["ok"], Literal["pending"], Literal["failed"]
    ]  # ok: full data, pending: still processing, failed: replay could not be parsed
    created: str
    id: str
    link: str
    uploader: UploaderData


class ReplayResult(BaseReplayResult):
    teams: Dict[
        str, dict
    ]  # team name, team data dict (examples are blue/orange but no idea really)
    visibility: str  # private/public
    title: str  # replay name
    map_code: str  # map internal name
    map_name: str  # map friendly name
    match_type: str  # Private, ...
    date: str  # game date (not upload date)
    duration: int  # how long game took (maybe also post 0:00 ?)
    overtime: bool  # got to overtime?
    overtime_seconds: int  # how long on overtime
    # NOTE: theres more data available but this is good for now


def get_replay(
    s: requests.Session, replay_id: str
) -> Union[BaseReplayResult, ReplayResult]:
    """TODO"""
    replay = s.get(f"{Config.replay_url}/{replay_id}")
    error_default: BaseReplayResult = {
        "id": replay_id,
        "status": "failed",
        "created": "",
        "link": "",
        "uploader": {"avatar": "", "name": "", "profile_url": ""},
    }
    if replay.status_code != 200:
        return error_default

    j = replay.json()  # : Union[BaseReplayResult, ReplayResult]
    status = j["status"]

    if status == "ok":
        ok: ReplayResult = j
        return ok

    if status == "failed" or status == "pending":
        failed_or_pending: BaseReplayResult = j
        return failed_or_pending

    return error_default
