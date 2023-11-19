class Printer:
    line_count: int = 0
    log = ""
    log_max_lines = 1000
    log_lines = 0

    @classmethod
    def print(cls, *args, **kwargs) -> None:
        """print() something"""
        line_count = 0
        for a in args:
            if type(a) is str:
                line_count += a.count("\n")
            else:
                line_count += 1
        print(*args, **kwargs)

        expected_lines = cls.log_lines + line_count
        over_amount = expected_lines - cls.log_max_lines
        if over_amount > 0:
            cls.log = cls.log[over_amount:]  # remove start lines

        cls.log += " ".join(
            [str(a) for a in args]
        )  # space is default behaviour of print i.e. what we printed
        cls.log_lines += line_count

        cls.line_count += line_count

    @classmethod
    def clear_lines(cls, count: int = 0) -> None:
        """Clear `count` lines to end of terminal.
        If `count == 0`, clears all lines."""
        c = cls.line_count if count == 0 else count
        c += 1  # TODO: for some reason n lines behind?
        if c == 0:
            return
        move_up = f"\033[{c}A"
        clear_to_end = "\33[J"
        print(move_up + clear_to_end, end="\r")
        cls.line_count = 0
