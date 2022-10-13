from pathlib import Path
from typing import Any

from yaml import YAMLError, dump, load

from todo.log import get_logger
from todo.model.observed import Observer, ObservedCollection, observable, Notify

try:
    from yaml import CDumper as Dumper
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader, Dumper  # type: ignore

from todo.error import YamlFileError

logger = get_logger(__name__, use_config=False)


class YamlFileObserver(Observer):
    _instance_cache: dict[Path, "YamlFileObserver"] = {}

    def __new__(cls, default_data, path: Path | str):
        if instance := cls._instance_cache.get(path):
            logger.info(f"Using cached instance of {instance}")
            return instance
        instance = super().__new__(cls)
        cls._instance_cache[path] = instance
        return instance

    def __init__(self, default_data, path: Path | str):  # type: ignore
        """
        Observer to serialize data to a yaml file.

        :param default_data: The data to be stored in the file. This is treated as default data if
        the file does not exist.
        :param path: The path to the file.
        """

        self.path = Path(path)

        def _default_data():
            dt = default_data() if callable(default_data) else default_data
            if dt is None:
                raise ValueError("default_data cannot be None")
            dt = observable(dt)
            self.dump(dt)
            return dt

        self._default_data = _default_data
        self._observed = None

    def to_observable(self) -> ObservedCollection:
        """
        Create an observable collection from the data in the file.
        """

        if (obs := getattr(self, "_observed", None)) is not None:
            return obs
        obs = observable(self.load())
        obs.attach(self)
        self._observed = obs
        return obs

    def load(self) -> Any:
        """
        Load the data. If the data is empty, create a file and save as specified
        in the default_data.
        """

        try:
            text: str = ""
            path: Path = self.path
            data: Any = None

            if path.exists():
                text = path.read_text(encoding="utf-8")
            if text:
                data = load(text, Loader=Loader)
            if data is None:
                logger.info("Loading default data")
                data = self._default_data()
            return data
        except YAMLError as e:
            raise YamlFileError(f"File is corrupted {e!r}", self.path) from e
        except IOError as e:
            raise YamlFileError(f"Unknown IOError {e!r} during loading", self.path) from e

    def dump(self: "YamlFileObserver", val: ObservedCollection) -> None:
        """
        Dump the data to the file.
        """

        try:
            path = self.path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                dump(val.root.to_data(), Dumper=Dumper),
                encoding="utf-8",
            )
        except IOError as e:
            raise YamlFileError(f"Unknown IOError {e!r} during dumping", self.path) from e

    def __call__(self, notify: Notify):
        self.dump(notify.observed)

    def __repr__(self):
        return f"{self.__class__.__name__}(path={self.path!r})"''
