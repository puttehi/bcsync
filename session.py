import requests

from common.config import Config
from common.printer import Printer

print = Printer.print
import datetime
from typing import List, Tuple

from tabulate import tabulate

from common.file_handlers import write_rotated_log
from common.string_manip import (center_pad_string, truncate_path_between,
                                 truncate_string)
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
            "success": "Uploaded: ",
            "duplicate": "Already uploaded: ",
        }

        runs = ""
        basename_col_width = 10
        padding = basename_col_width * 4
        pad_char = "."
        for run_result in cls.run_results:
            rows = []
            for rd in run_result["replaydatas"]:
                result = rd["result"]
                id = rd["id"]
                # url = rd["url"]
                watch_url = rd["watch_url"]
                info = result_map.get(result, "") + id + "\n"
                lines = 1
                basename = ""
                if Config.print_viewer_url:
                    info += watch_url
                    lines += 1
                    bn = rd["basename"]
                    basename = (
                        bn[:basename_col_width]
                        + "\n"
                        + truncate_string(
                            bn[basename_col_width:],
                            length=basename_col_width,
                            ending="...",
                        )
                    )
                else:
                    basename = truncate_string(
                        rd["basename"], length=basename_col_width, ending="..."
                    )
                rows.append((basename, info))

            table = tabulate(rows)

            timestamp = str(run_result["timestamp"])
            report_length = len(table.split("\n")[0])
            body = (
                center_pad_string(
                    string=str(timestamp),
                    line_length=report_length,
                    ws_pad_count=6,
                    pad_char=".",
                )
                + table
                + "\n"
            )

            runs += body

        return runs

    @classmethod
    def write_report_to_file(cls) -> None:
        """Write session report to `Config.session_log_file_identifier`.log"""
        head = cls.create_header_table()
        body = cls.create_report_body()

        log = f"{head}\n{body}"

        write_rotated_log(identifier=Config.session_log_file_identifier, text=log)

        return
