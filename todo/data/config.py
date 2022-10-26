from todo.globals import data_path, cache_path, log_path, config_path
from todo.log import get_logger
from todo.data.observers import YamlFileObserver
from todo.data.observed import ObservedDot

logger = get_logger(__name__, use_config=False)


def _default_config():
    logger.info("Generate default config.")
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


config = ObservedDot(YamlFileObserver(_default_config, config_path / "config.yaml").to_observable())
