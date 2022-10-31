import datetime
from typing import List, TypedDict, Union

from replay import ExtendedReplayData, ReplayData


class RunResult(TypedDict):
    timestamp: datetime.datetime
    replaydatas: List[Union[ExtendedReplayData, ReplayData]]
