import logging
from pathlib import Path

from todo.error import NeedConfigError
from todo.globals import log_path as default_log_path


def get_logger(
    name=None,
    use_config: bool = True,
    level: int = None,
    log_path: Path = None,
    log_file: str = None,
) -> logging.Logger:
    """
    Get a logger with the given name and level.

    :param name: the name of the logger
    :param level: the level of the logger
    :param use_config: whether to use the config to set the level and log path
    :param log_path: specify the log path
    :param log_file: specify the log file, relative to the log path
    :return: logger
    """

    if use_config:
        from todo.model import config

        if log_file or log_path or level:
            raise ValueError(
                "Cannot specify log_path, log_file, or level when use_config is True."
            )
        try:
            level = getattr(logging, config.logging.level)
        except AttributeError:
            raise NeedConfigError("logging.level", "Level of logging.")
        log_path = config.logging.path
    if log_path is None:
        log_path = default_log_path / "todo.log"
    if level is None:
        level = logging.DEBUG
    if log_file:
        log_path = log_path.parent / log_file

    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(level)

    fh = logging.FileHandler(log_path)
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
    return logger