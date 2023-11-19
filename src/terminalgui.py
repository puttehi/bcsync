from typing import Protocol
from printer import Printer
from gui import GUI

print = Printer.print

class TerminalGUI(GUI):
    session_data = {}

    def __init__(self):
        pass

    def build(self):
        return

    def run(self):
        return

    def clear_lines(self, count=0) -> None:
        Printer.clear_lines(count)

    def print(self, *args, **kwargs) -> None:
        Printer.print(*args, **kwargs)

    def print_replay_attributes(self, replay: Replay) -> str:
        """Print Replay object attributes and return the printed string."""
        printed = f"{'8<':-^20}\n"
        printed += str(vars(replay)) + "\n"
        printed += f"{'>8':-^20}\n"
        self.print(printed)

        return printed

