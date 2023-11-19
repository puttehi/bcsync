from nicegui import ui
from session import Session
from gui import GUI



class State():
    total_replays = Session.session_data["total_replays"]


class WebGUI(GUI):
    session_data: SessionData

    def __init__(self):
        session_data = Session.session_data


    def build():
        ui.markdown("# Session statistics")
        ui.markdown("## Totals")
        ui.markdown("### Replay count:")
        ui.number().bind_value(State, "total_replays")


    def run():
        ui.run()
