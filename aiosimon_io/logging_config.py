"""
Logging configuration for the aiosimon_io package.

This module provides a function to set up logging with a specified level and format.
"""

import logging
from typing import Union


def setup_logging(level: Union[int, str] = logging.DEBUG) -> None:
    """
    Set up logging configuration.

    Args:
        level (Union[int, str]): Logging level, can be an integer or string.

    :canonical: aiosimon_io.logging_config.setup_logging()
    """
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )
