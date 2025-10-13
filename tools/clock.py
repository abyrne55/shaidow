from datetime import datetime, timezone
from llm import Toolbox

class Clock(Toolbox):
    """
    A simple time management tool
    """
    def __init__(self):
        """
        Initialize the Clock
        """
        super().__init__()
        self.stopwatch_start_time = None

    def local_time(self) -> str:
        """
        Get the current time in the local timezone in ISO 8601 format
        """
        return datetime.now().isoformat(timespec='milliseconds')

    def utc_time(self) -> str:
        """
        Get the current time in the UTC timezone in ISO 8601 format
        """
        return datetime.now(timezone.utc).isoformat(timespec='milliseconds')

    def start_stopwatch(self) -> str:
        """
        Start a stopwatch
        """
        self.stopwatch_start_time = datetime.now()
        return "Stopwatch started. Use check_stopwatch to check the elapsed time."

    def check_stopwatch(self) -> str:
        """
        Check the stopwatch
        """
        if self.stopwatch_start_time is None:
            return "No stopwatch has been started. Use start_stopwatch to start a stopwatch."
        return f"It's been {datetime.now() - self.stopwatch_start_time} since the last call to start_stopwatch."