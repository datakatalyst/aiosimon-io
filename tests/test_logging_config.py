import logging

from aiosimon_io.logging_config import setup_logging


def test_setup_logging_default_level():
    logging.getLogger().handlers.clear()
    logging.getLogger().setLevel(logging.NOTSET)

    setup_logging()
    logger = logging.getLogger()

    assert logger.level == logging.DEBUG
    assert len(logger.handlers) == 1
    assert isinstance(logger.handlers[0], logging.StreamHandler)


def test_setup_logging_error_level():
    logging.getLogger().handlers.clear()
    logging.getLogger().setLevel(logging.NOTSET)

    setup_logging(logging.ERROR)
    logger = logging.getLogger()

    assert logger.level == logging.ERROR
    assert len(logger.handlers) == 1
    assert isinstance(logger.handlers[0], logging.StreamHandler)
