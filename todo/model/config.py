from functools import cached_property

from todo.globals import config_path, data_path, cache_path, log_path
from todo.log import get_logger
from todo.model.observables import ObservableDict
from todo.model.yamlfile import YamlFile
from todo.utils import delegate

logger = get_logger(__name__, use_config=False)


@delegate(target=ObservableDict, name="data")
class Config:
    DEFAULT_CONFIG_PATH = config_path / "config.yaml"

    def __init__(self, path=None):
        if path is None:
            logger.info(f"Using default config path {path}.")
            path = self.DEFAULT_CONFIG_PATH
        logger.debug(f"Using config path {path}.")
        self.data = YamlFile(data=ObservableDict({}), path=path)
        if self.data == {}:
            logger.warning("Config file is empty. Using default values.")
            self.data.update(self.default_config)

    @cached_property
    def default_config(self):
        return {
            "first_time": True,
            "logging": {"level": "DEBUG", "path": log_path / "todo.log"},
            "paths": {
                "db": data_path / "todo.db",
                "cookies": cache_path / "cookies",
                "navigators": cache_path / "navigators",
            },
            "integration": {
                "enabled": True,
                "interval": 60,
            },
            "integrations": {},
        }


config = Config(Config.DEFAULT_CONFIG_PATH)
