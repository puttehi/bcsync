from typing import Any


class Config:
    verbosity = 0

    @classmethod
    def set_verbosity(cls, verbosity: int) -> None:
        cls.verbosity = verbosity
