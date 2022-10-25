from typing import IO, Any, Literal, Mapping, TypedDict

import requests

from common.config import Config


def make_url_param(key: str, value: str) -> str:
    """Format key, value pair to ?key=value"""
    return f"?{key}={value}"


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


class UploadResult(TypedDict):
    status_code: int  # HTTP status code
    json: dict  # response json
    result: Literal[
        "success", "duplicate", "fail"
    ]  # success: new upload, duplicate: already exists, fail: something is wrong
    id: str  # ballchasing.com replay id


def upload_replay(
    s: requests.Session, file_: Mapping[str, IO], visibility: str = "private"
) -> UploadResult:
    """Upload a replay `file_` to ballchasing.com
    Returns:
        (UploadResult): Result of the upload attempt."""
    url_params = make_url_param('visibility', visibility)
    upload = s.post(f"{Config.upload_url}{url_params}", files=file_)

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


class UploaderInfo(TypedDict):
    avatar: str # Steam profile pic link
    name: str # Steam name
    profile_url: str # Steam profile url

class BaseReplayData(TypedDict):
    created: str # YYYY-MM-DDTHH:mm:SS.ssssssZ
    id: str # replay id
    link: str # same as fetch url: <replay_url>/<id>
    uploader: UploaderInfo

class ReplaysResponse(TypedDict):
    count: int # Count of replay datas in `list`
    list: List[dict] # List of replay datas
    next: str # Fetch next page here


def get_replays(s: requests.Session, url: str = Config.get_replay_url, filters: dict = {}) -> Tuple[List[dict], str]:
    """Get replays with filters. Pass in `next_url` of the previous
    return value to `url` to keep going through pages.
    For filters: https://ballchasing.com/doc/api#replays-replays-get
    Returns:
        (Tuple[List[dict], str]): List of replay data objects and `next_url` for next page of results."""
    url_params = "".join([make_url_param(key, value) for key, value in filters.items()])
    response = s.get(f"{url}{url_params}")

    if response.status_code != 200:
        if Config.verbosity > 0:
            print(f"Fetching replays failed")
        return [], ""
    
    j: ReplaysResponse = response.json()

    return j["list"], j["next"]


class ReplayResponse(BaseReplayData):
    status: Union[Literal["failed"], Literal["ok"], Literal["pending"]] # Replay upload status

def get_replay(s: requests.Session, replay_id: str) -> ...:
    """Get replay with replay ID.
    Returns:
        (): ..."""
    response = s.get(f"{Config.get_replay_url}/{replay_id}")

    if response.status_code != 200:
        if Config.verbosity > 0:
            print(f"Fetching replay {replay_id} failed")
        return ...
    
    j: ... = response.json()

    status = j["status"]
    if status == "ok":
        pass
    elif status == "failed":
        pass
    elif status == "pending"
