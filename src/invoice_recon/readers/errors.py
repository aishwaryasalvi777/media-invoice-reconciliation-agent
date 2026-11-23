"""The error every bill reader raises when a bill can't be read cleanly."""


class InvoiceReadError(Exception):
    """A bill has problems. `problems` lists every one of them."""

    def __init__(self, problems: list[str]) -> None:
        self.problems = problems
        listed = "\n".join(f"- {p}" for p in problems)
        super().__init__(f"{len(problems)} problem(s) reading the bill:\n{listed}")
