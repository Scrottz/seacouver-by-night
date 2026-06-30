import logging
import sys

FMT = "%(asctime)s | %(levelname)s | %(name)s:%(lineno)d | %(message)s"


def get_logger(name: str):
    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.setLevel(logging.INFO)

        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(FMT)
        handler.setFormatter(formatter)

        logger.addHandler(handler)

    return logger


