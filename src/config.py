from os import path
from typing import Any


class Config:
    verbosity = 0  # Log verbosity [v]+
    api_token = ""  # ballchasing.com API token
    replay_path = ""  # Path to read replay(s) from
    watch = 0  # Sleep time ms between loops. 0: Run once only
    print_viewer_url = False  # Print ballchasing.com 3D viewer url in session logs
    web_url = "https://ballchasing.com"
    api_url = f"{web_url}/api"
    upload_url = f"{api_url}/v2/upload"
    replay_url = f"{api_url}/replays"
    duplicates_file = "known_duplicates.db"
    working_directory = ""
    session_log_file_identifier = "session"
    max_session_logfiles = 10
    show_extended_results = False  # make additional api call for each replay metadata

    @classmethod
    def set_verbosity(cls, verbosity: int) -> None:
        cls.verbosity = verbosity

    @classmethod
    def set_api_token(cls, api_token: str) -> None:
        cls.api_token = api_token

    @classmethod
    def set_replay_path(cls, replay_path: str) -> None:
        cls.replay_path = replay_path

    @classmethod
    def set_watch(cls, watch: int) -> None:
        cls.watch = watch

    @classmethod
    def set_duplicates_file(cls, duplicates_file: str) -> None:
        cls.duplicates_file = duplicates_file

    @classmethod
    def set_print_viewer_url(cls, print_viewer_url: bool) -> None:
        cls.print_viewer_url = print_viewer_url

    @classmethod
    def set_working_directory(cls, working_directory: str) -> None:
        cls.working_directory = working_directory

    @classmethod
    def set_show_extended_results(cls, show_extended_results: bool) -> None:
        cls.show_extended_results = show_extended_results
