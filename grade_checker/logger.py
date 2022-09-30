import logging
from grade_checker.config import cfg

def criteria(criteria=bool):
    def print_args(func):
        def _impl(*args, **kwargs):
            res = func(*args, **kwargs)
            if criteria(res):
                logger.debug(f"{func.__name__}({args}, {kwargs}) returns {res}")
            return res

        return _impl

    return print_args


def _init():
    logger = logging.getLogger("grade_checker")
    logger.setLevel(logging.DEBUG)

    fh = logging.FileHandler(cfg.grade_checker.log_path)
    fh.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    ch.setLevel(logging.ERROR)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


logger = _init()
