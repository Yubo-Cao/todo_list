import logging


def get_logger(name=None, level: int = logging.INFO) -> None:
    from todo.model.config import config

    logger = logging.getLogger(name)
    logger.setLevel(level)

    fh = logging.FileHandler(config.paths.log)
    fh.setLevel(level)

    ch = logging.StreamHandler()
    ch.setLevel(level)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)
