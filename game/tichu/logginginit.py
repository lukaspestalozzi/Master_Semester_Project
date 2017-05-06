import logging
import os
import errno


def make_sure_path_exists(path):
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise


def initialize_logger(output_dir, console_log_level, info_log="info.log", warn_err_log="warn_error.log", all_log="all.log", verbose=True):
    """
    
    :param output_dir: 
    :param console_log_level: 
    :param logsname: The logs go into a folder with this name, if it is a string
    :param info_log: 
    :param warn_err_log: 
    :param all_log: 
    :param verbose: if True, prints to stdout which handlers have been set.
    :return: 
    """
    # datefmt='%Y.%m.%d %H:%M:%S'
    make_sure_path_exists(output_dir)

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # create console handler and set level to info
    if console_log_level:
        handler = logging.StreamHandler()
        handler.setLevel(console_log_level)
        formatter = logging.Formatter('%(process)d: %(levelname)s [%(module)s]:%(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        if verbose:
            print("console_log_level is", str(console_log_level))

    # create INFO file handler and set level to error
    if info_log:
        handler = logging.FileHandler(os.path.join(output_dir, info_log), "w", encoding=None)
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(process)d: %(levelname)s [%(module)s]:%(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        if verbose:
            print("info_log is", info_log)

    # create error file handler and set level to WARNING
    if warn_err_log:
        handler = logging.FileHandler(os.path.join(output_dir, warn_err_log), "w", encoding=None, delay="true")
        handler.setLevel(logging.WARNING)
        formatter = logging.Formatter('%(process)d: %(levelname)s [%(module)s]:%(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        if verbose:
            print("warn_err_log is", warn_err_log)

    # create debug file handler and set level to debug
    if all_log:
        handler = logging.FileHandler(os.path.join(output_dir, all_log), "w")
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(process)d: %(levelname)s [%(module)s]:%(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        if verbose:
            print("all_log is", all_log)

    if verbose:
        print("Logging to:", output_dir)
