import requests

from common.config import Config
from common.printer import Printer

print = Printer.print
import datetime
from typing import List, Tuple

from tabulate import tabulate

from common.file_handlers import write_rotated_log
from common.string_manip import (center_pad_string, seconds_to_mm_ss,
                                 truncate_path_between, truncate_string,
                                 wrap_and_truncate_string)
from replay import Replay
from runner import RunResult


class Session:
    # Historical/Totals
    total_replays: int = 0  # Total replays in ballchasing
    total_duplicates: int = 0  # Total duplicates
    old_duplicates: int = 0  # Total old duplicates that were skipped
    # Session
    new_uploads: int = 0  # Total new uploads
    new_duplicates: int = 0  # Total new duplicate entries in local .db
    # body_log: str = "" # Session log (body text only)
    run_results: List[RunResult]  # List of run results (where a request was sent)
    session: requests.Session | None = None  # requests Session for keeping auth info

    @classmethod
    def update_session_statistics(
        cls, replays: List[Replay], run_result: RunResult
    ) -> None:
        cls.new_uploads += len([r for r in replays if r.upload_result == "success"])
        cls.old_duplicates = len(
            [r for r in replays if r.upload_result == "" and r.duplicate is True]
        )
        cls.new_duplicates += len(
            [r for r in replays if r.upload_result == "duplicate"]
        )

        cls.total_duplicates = cls.old_duplicates + cls.new_duplicates
        cls.total_replays = cls.total_duplicates + cls.new_uploads

        if len(run_result["replaydatas"]) > 0:
            # had upload attempts
            cls.run_results.append(run_result)

        return

    @classmethod
    def print_header(cls):
        header = cls.create_header_table()
        print(header)

    @classmethod
    def create_header_table(
        cls,
    ) -> str:
        """Create header table"""
        replay_path = truncate_path_between(Config.replay_path)
        timestamp = datetime.datetime.now()
        return tabulate(
            [
                ["Last synced on", timestamp],
                ["Replay path", replay_path],
                ["New uploads", cls.new_uploads],
                ["New duplicates", cls.new_duplicates],
                ["Total replays", cls.total_replays],
            ]
        )

    @classmethod
    def print_body(cls):
        """"""
        body = cls.create_report_body()
        print(body)

    @classmethod
    def create_report_body(cls) -> str:
        """"""
        result_map = {
            "success": " (new upload)",
            "duplicate": " (already uploaded)",
        }

        runs = ""
        basename_col_width = 10
        pad_char = "."
        ws_pad_count = 6
        for run_result in cls.run_results:
            rows = []
            for rd in run_result["replaydatas"]:
                result = rd["result"]
                id_ = rd["id"]
                # url = rd["url"]
                rows.append(("Filename", rd["basename"]))
                rows.append(("Replay ID", id_ + result_map.get(result, "")))
                if Config.print_viewer_url:
                    watch_url = rd["watch_url"]
                    rows.append(("Watch URL", watch_url))
                if Config.show_extended_results and rd.get("json", None) is not None:
                    # : BaseReplayResult if status not "ok" | ReplayResult if status "ok"
                    j = rd["json"]
                    if j["status"] == "ok":
                        rows.append(("Title", j.get("title", "Unknown title")))
                        rows.append(("Played on", j.get("date", "Unknown date")))
                        rows.append(
                            ("Map", j.get("map_name", j.get("map_code", "Unknown map")))
                        )
                        duration = seconds_to_mm_ss(j.get("duration", 0))
                        if j["overtime"]:
                            duration += (
                                " (On OT: "
                                + seconds_to_mm_ss(j["overtime_seconds"])
                                + ")"
                            )
                        rows.append(("Duration", duration))

            table = tabulate(rows)

            timestamp = run_result["timestamp"]
            report_length = len(table.split("\n")[0])
            body = (
                center_pad_string(
                    string=str(timestamp),
                    line_length=report_length,
                    ws_pad_count=ws_pad_count,
                    pad_char=pad_char,
                )
                + table
                + "\n"
            )

            runs += body

        return runs

    @classmethod
    def write_report_to_file(cls) -> None:
        """Write session report to `Config.session_log_file_identifier`.log"""
        write_rotated_log(
            identifier=Config.session_log_file_identifier, text=Printer.log
        )

        return
