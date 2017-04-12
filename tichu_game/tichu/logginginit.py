import logging
import os.path


def initialize_logger(output_dir, console_log_level, info_log="info.log", warn_err_log="warn_error.log", all_log="all.log"):
    # datefmt='%Y.%m.%d %H:%M:%S'

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # create console handler and set level to info
    if console_log_level:
        handler = logging.StreamHandler()
        handler.setLevel(console_log_level)
        formatter = logging.Formatter('%(levelname)s [%(module)s]:%(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    # create INFO file handler and set level to error
    if info_log:
        handler = logging.FileHandler(os.path.join(output_dir, info_log), "w", encoding=None)
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(levelname)s [%(module)s]:%(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    # create error file handler and set level to WARNING
    if warn_err_log:
        handler = logging.FileHandler(os.path.join(output_dir, warn_err_log), "w", encoding=None, delay="true")
        handler.setLevel(logging.WARNING)
        formatter = logging.Formatter('%(levelname)s [%(module)s]:%(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    # create debug file handler and set level to debug
    if all_log:
        handler = logging.FileHandler(os.path.join(output_dir, all_log), "w")
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(levelname)s [%(module)s]:%(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)