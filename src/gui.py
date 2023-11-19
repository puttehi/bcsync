from replay import Replay
from session import SessionData

class GUI(Protocol):
    session_data: SessionData

    def build():
        ...

    def run():
        ...

    def clear_lines(count: int) -> None:
        ...

    def print(*args, **kwargs) -> None:
        ...

    def print_replay_attributes(self, replay: Replay) -> str:
        ...

