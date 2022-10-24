from typing import Any


class Config:
    verbosity = 0  # Log verbosity [v]+
    api_token = ""  # ballchasing.com API token
    replay_path = ""  # Path to read replay(s) from
    watch = 0  # Sleep time ms between loops. 0: Run once only

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
