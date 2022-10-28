#!/usr/bin/env python
"""Replay data container class definition"""
import os
from typing import List, Literal, TypedDict, Union

import requests

import ballchasing_api
from ballchasing_api import BaseResult
from common.config import Config
from common.printer import Printer

print = Printer.print


class ReplayData(BaseResult):
    basename: str
    url: str
    watch_url: str


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

    def upload(self, session: requests.Session) -> Union[ReplayData, None]:
        """Upload the replay to ballchasing.com."""
        if self.duplicate:
            if Config.verbosity > 0:
                print(f"Skipping known duplicate: {self.basename}")
            return None

        upload_result = ballchasing_api.upload_replay(
            s=session, file_={"file": open(self.path, "rb")}, visibility=self.visibility
        )

        self.upload_json = upload_result["json"]
        self.ballchasing_id = upload_result["id"]
        self.upload_result = upload_result["result"]

        url = f"{Config.web_url}/replay/{self.ballchasing_id}"
        replay_data: ReplayData = {
            "result": self.upload_result,
            "id": self.ballchasing_id,
            "basename": self.basename,
            "url": url,
            "watch_url": f"{url}#watch",
        }

        return replay_data

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
