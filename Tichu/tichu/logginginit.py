import logging
import os.path


def initialize_logger(output_dir, console_log_level):
    # datefmt='%Y.%m.%d %H:%M:%S'

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # create console handler and set level to info
    handler = logging.StreamHandler()
    handler.setLevel(console_log_level)
    formatter = logging.Formatter('%(levelname)s [%(module)s]:%(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # create INFO file handler and set level to error
    handler = logging.FileHandler(os.path.join(output_dir, "info.log"), "w", encoding=None)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(levelname)s [%(module)s]:%(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # create error file handler and set level to WARNING
    handler = logging.FileHandler(os.path.join(output_dir, "warn_error.log"), "w", encoding=None, delay="true")
    handler.setLevel(logging.WARNING)
    formatter = logging.Formatter('%(levelname)s [%(module)s]:%(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # create debug file handler and set level to debug
    handler = logging.FileHandler(os.path.join(output_dir, "all.log"), "w")
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(levelname)s [%(module)s]:%(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)