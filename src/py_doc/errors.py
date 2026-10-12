"""Errors shared by the renderers and the tool runner."""


class ConversionError(Exception):
    """The input cannot be converted (for example, it is not valid UTF-8)."""


class EnvironmentProblem(ConversionError):
    """The machine cannot run the step: an unsupported platform, or a missing engine or image.

    The input is not at fault, so commands report it with exit status 2 instead of 1.
    """


def exit_status(error: BaseException) -> int:
    """The exit status for a failure: 2 for an environment problem, 1 for anything else."""
    return 2 if isinstance(error, EnvironmentProblem) else 1


class ToolFailed(ConversionError):
    """An external tool ran and failed. The full output is kept, because it says why."""

    def __init__(self, tool: str, returncode: int | None, output: str, reason: str | None = None):
        self.tool = tool
        self.returncode = returncode
        self.output = output.strip()
        status = reason or f"failed with exit status {returncode}"
        detail = f":\n{self.output}" if self.output else ""
        super().__init__(f"{tool} {status}{detail}")


class ToolTimeout(ToolFailed):
    """A tool did not finish in the time allowed."""

    def __init__(self, tool: str, seconds: float, output: str = ""):
        super().__init__(tool, None, output, reason=f"did not finish within {seconds:g} seconds")
