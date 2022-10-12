import asyncio
import logging
import warnings
from abc import abstractmethod
from functools import cached_property

from todo.log import get_logger
from todo.model import config, Config
from todo.globals import log_path

logger = get_logger(__name__, use_config=False, log_path=log_path / "integration.log")


class Integration:
    """
    Abstract class for integrations.
    """

    def __init_subclass__(cls, **kwargs):
        logger.debug(f"Registering integration {cls.__name__}")

        def new(cl, *args, **kwargs):
            if (instance := getattr(cl, "_instance", ...)) is ...:
                instance = cl._instance = super(cl, cl).__new__(cl)
            return instance

        if "__new__" in cls.__dict__:
            warnings.warn("Integration class already has __new__ method, overwriting.")
        cls.__new__ = new

    @property
    def config_path(self) -> str:
        """
        Get the path of the integration config.
        """

        return f"integrations.{self.__class__.__name__}"

    @cached_property
    def config(self) -> Config:
        """
        Get the configuration of the integration.
        """

        return config.setdefault("integrations", {}).setdefault(
            self.__class__.__name__, {}
        )

    @cached_property
    def logger(self) -> logging.Logger:
        """
        Get a logger for the integration.
        """

        return get_logger(
            self.__class__.__name__,
            use_config=False,
            log_path=log_path / f"{self.__class__.__name__}.log",
        )

    def log(self, level: int, message: str, *args, **kwargs) -> None:
        """
        Log a message.
        """

        self.logger.log(level, message, *args, **kwargs)

    def error(self, message: str, *args, **kwargs) -> None:
        """
        Log an error.
        """

        self.log(logging.ERROR, message, *args, **kwargs)

    def warning(self, message: str, *args, **kwargs) -> None:
        """
        Log a warning.
        """

        self.log(logging.WARNING, message, *args, **kwargs)

    def info(self, message: str, *args, **kwargs) -> None:
        """
        Log an info message.
        """

        self.log(logging.INFO, message, *args, **kwargs)

    def debug(self, message: str, *args, **kwargs) -> None:
        """
        Log a debug message.
        """

        self.log(logging.DEBUG, message, *args, **kwargs)

    @abstractmethod
    async def update(self) -> None:
        """
        Update the in the model.
        """

    async def run(self) -> None:
        """
        Run the integration.
        """

        if not config.integration.enabled:
            logger.info("Integration is disabled.")
            return

        while True:
            try:
                await self.update()
            except Exception as e:
                logger.error(f"Error while updating {self.__class__.__name__}: {e!r}")
            await asyncio.sleep(config.integration.interval)
