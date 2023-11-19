#!/usr/bin/env python
"""Replay data container class definition"""
import os
from typing import List, Literal, TypedDict, Union

from gui import GUI
import requests

import ballchasing_api
from ballchasing_api import BaseReplayResult, BaseResult, ReplayResult
from config import Config
from string_manip import truncate_string

class ReplayData(BaseResult):
    basename: str
    url: str
    watch_url: str


class ExtendedReplayData(ReplayData):
    json: Union[
        BaseReplayResult, ReplayResult
    ]  # can check type from 'status' ('ok' is full data)


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
            self, session: requests.Session, gui: Optional[GUI] = None
    ) -> Union[ReplayData, ExtendedReplayData, None]:
        """Upload the replay to ballchasing.com."""
        if self.duplicate:
            if Config.verbosity > 0 and gui is not None:
                gui.print(f"Skipping known duplicate: {self.basename}")
            return None

        status_length = 28
        if Config.verbosity == 0 and gui is not None:
            request_log = f"Out: {self.basename}"
            gui.print(truncate_string(request_log, status_length), end="\r")

        upload_result = ballchasing_api.upload_replay(
            s=session, file_={"file": open(self.path, "rb")}, visibility=self.visibility
        )

        self.upload_json = upload_result["json"]
        self.ballchasing_id = upload_result["id"]
        self.upload_result = upload_result["result"]

        url = f"{Config.web_url}/replay/{self.ballchasing_id}"

        rd: ReplayData = {
            "result": self.upload_result,
            "id": self.ballchasing_id,
            "basename": self.basename,
            "url": url,
            "watch_url": f"{url}#watch",
        }
        ret = rd
        if Config.show_extended_results:
            extended_rd: ExtendedReplayData = {
                "result": rd["result"],
                "id": rd["id"],
                "basename": rd["basename"],
                "url": rd["url"],
                "watch_url": rd["watch_url"],
                "json": ballchasing_api.get_replay(
                    s=session, replay_id=self.ballchasing_id
                ),
            }
            ret = extended_rd

        if Config.verbosity > 0 and gui is not None:
            result = ret["result"]
            basename = ret["basename"]
            response_log = f"In: {result} {basename}\n"
            gui.print(truncate_string(response_log, status_length))

        return ret

    @classmethod
    def read_known_duplicates(cls) -> List[str]:
        try:
            with open(Config.duplicates_file, "r") as f:
                duplicates = [
                    l.strip() for l in f.readlines() if l != "\n"
                ]  # strip newlines from the raw read and disregard line breaks
                cls.known_duplicates = duplicates
                return duplicates
        except FileNotFoundError as e:
            return []

    known_duplicates: List[str] = []
