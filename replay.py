#!/usr/bin/env python
"""Replay data container class definition"""
from typing import List, Literal, Union

import requests

import ballchasing_api
from common.config import Config


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
        self, session: requests.Session
    ) -> Union[
        Literal["success"],
        Literal["duplicate"],
        Literal["fail"],
        Literal["old_duplicate"],
    ]:
        """Upload the replay to ballchasing.com.
        Returns:
            "old_duplicate": if the replay was already uploaded before
            "duplicate": if a previously uploaded replay already exists
            "success": if a new upload was successful
            "fail": if the upload failed horribly"""
        if self.duplicate:
            if Config.verbosity > 0:
                print(f"Skipping known duplicate: {self.basename}")
            return "old_duplicate"

        upload_result = ballchasing_api.upload_replay(
            s=session, file_={"file": open(self.path, "rb")}, visibility=self.visibility
        )

        self.upload_json = upload_result["json"]
        self.ballchasing_id = upload_result["id"]
        self.upload_result = upload_result["result"]

        return self.upload_result

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
