from typing import Callable, Optional


class ProgressNotifier:
    """Reports progress during long-running operations.

    Default implementation prints to stdout.
    Override `on_progress` to route messages elsewhere (e.g. Discord).
    """

    def __init__(self, callback: Optional[Callable[[str], None]] = None):
        self._callback = callback or print

    def update(self, message: str) -> None:
        self._callback(message)
