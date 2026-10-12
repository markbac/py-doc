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
