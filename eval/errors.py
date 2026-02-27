class AnchorDomainError(ValueError):
    """Base exception for all anchor-related domain errors."""

    pass


class AnchorNotFoundError(AnchorDomainError):
    """Raised when an anchor or golden set cannot be found."""

    pass


class ScenarioMismatchError(AnchorDomainError):
    """Raised when the requested scenario does not match the loaded dataset's scenario."""

    pass


class GoldenSetNotFoundError(AnchorDomainError):
    """Raised when a specified golden set file cannot be found."""

    pass


class RunNotFoundError(ValueError):
    """Raised when an evaluation run cannot be found."""

    pass
