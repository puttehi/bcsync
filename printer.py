class Printer:
    line_count: int = 0

    @classmethod
    def print(cls, *values, **kwargs) -> None:
        """print() something"""
        string = " ".join(
            list(values)
        )  # print() like behaviour but we want to count lines
        lines = string.split("\n")
        line_count = len(lines)
        print(string, **kwargs)
        cls.line_count += line_count

    @classmethod
    def clear_lines(cls, count: int = 0) -> None:
        """Clear `count` lines to end of terminal.
        If `count == 0`, clears all lines."""
        c = count
        if count == 0:
            c = cls.line_count
        move_up = f"\033[{c}A"
        clear_to_end = "\33[J"
        print(move_up + clear_to_end, end="\r")
        cls.line_count = 0
