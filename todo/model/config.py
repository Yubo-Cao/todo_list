from todo.globals import config_path, data_path, cache_path, log_path
from todo.log import get_logger
from todo.model.yamlfile import YamlFile
from functools import cached_property

logger = get_logger(__name__, use_config=False)


class Config:
    DEFAULT_CONFIG_PATH = config_path / "config.yaml"

    def __init__(self, path=None, _parent=None):
        if path is None and _parent is None:
            logger.debug(f"Using default config path {path}.")
            path = self.DEFAULT_CONFIG_PATH
        logger.info(f"Using config path {path}.")
        self.config = YamlFile(path, _parent=_parent)
        if self.config == {}:
            logger.warning("Config file is empty. Using default values.")
            self.config.update(self.default_config)

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

    def __getattribute__(self, item):
        dct = super().__getattribute__("__dict__")
        if (result := dct.get(item)) is not None:
            return result
        return getattr(self.config, item)


config = Config(Config.DEFAULT_CONFIG_PATH)
