from todo.globals import config_path, data_path, cache_path, log_path
from todo.log import get_logger
from todo.model.yamlfile import YamlFile

logger = get_logger(__name__, use_config=False)


class Config(YamlFile):
    DEFAULT_CONFIG_PATH = config_path / "config.yaml"

    def __init__(self, path=None, _parent=None):
        if path is None and _parent is None:
            logger.debug(f"Using default config path {path}.")
            path = self.DEFAULT_CONFIG_PATH
        logger.info(f"Using config path {path}.")
        super().__init__(path, _parent)

    def _load(self):
        super()._load()
        if self._data == {}:
            logger.info("Apply default configurations")
            self._data = {
                "first_time": True,
                "logging": {
                    "level": "DEBUG",
                    "path": log_path / "todo.log"
                },
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
            self._dump()


config = Config(Config.DEFAULT_CONFIG_PATH)
