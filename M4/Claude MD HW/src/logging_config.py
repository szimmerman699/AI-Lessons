"""Structured logging configuration using structlog."""

import structlog


def configure_logging() -> None:
    """Initialize structlog with standard configuration."""
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.PrintLogger:
    """Get a configured structlog logger instance.

    Args:
        name: Logger name, typically __name__ of the calling module.

    Returns:
        Configured structlog logger.
    """
    return structlog.get_logger(name)
