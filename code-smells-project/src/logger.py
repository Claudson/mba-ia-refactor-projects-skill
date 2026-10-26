import logging

LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


def configure_logging(level="INFO"):
    logging.basicConfig(level=level, format=LOG_FORMAT)


def get_logger(name):
    return logging.getLogger(name)
