"""Input errors that carry a machine-readable code and the offending field.

`InputError` subclasses ValueError, so older callers that catch ValueError keep working.
The codes are the ones in CONTRACT.md §2.4; the contract layer passes them through.
"""


class InputError(ValueError):
    def __init__(self, message: str, code: str = "INVALID_VALUE", field: str | None = None):
        super().__init__(message)
        self.code = code
        self.field = field
