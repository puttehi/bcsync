import datetime
from typing import List, TypedDict

from replay import ReplayData


class RunResult(TypedDict):
    timestamp: datetime.datetime
    replaydatas: List[ReplayData]
