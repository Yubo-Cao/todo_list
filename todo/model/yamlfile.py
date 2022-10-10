from collections.abc import Iterable
from pathlib import Path
from typing import Optional

from todo.model.observables import ObservableDict, observable
from yaml import YAMLError, dump, load

try:
    from yaml import CDumper as Dumper
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader, Dumper

from todo.error import YamlFileError
from todo.log import get_logger

logger = get_logger(__name__, use_config=False)


class YamlFile:
    def __init__(
        self,
        path: Path | str,
        _parent: Optional["YamlFile"] = None,
    ):
        """
        Represents a YAML file. Provide access to the data in the file as a
        dictionary. If the file does not exist, it will be created.
        You can use file.attr to access the data in the file, and file.attr = x
        to set the value of attr to x.

        :param path: The path to the file.
        :param _parent: Internal use only.
        """

        if path is None and _parent is None:
            raise ValueError("Path must not be None.")
        elif path is not None and _parent is not None:
            raise ValueError("Do not pass any argument for parent.")
        elif path is not None:
            self.__dict__["path"] = Path(path)
            self._load()
        else:
            self.__dict__["_parent"] = _parent

    def __setitem__(self, key, item):
        self._data[key] = item

    def __getitem__(self, key):
        return self._iterable_wrapper(self._data[key])

    def __delitem__(self, key):
        del self._data[key]

    def __contains__(self, key):
        return key in self._data

    def __len__(self):
        return len(self._data)

    def __repr__(self):
        return f"{self.__class__.__name__}({self._data!r})"

    def __str__(self):
        return str(self._data)

    def __iter__(self):
        return (self._iterable_wrapper(x) for x in self._data)

    _PLACEHOLDER = object()

    def __getattr__(self, name, default=_PLACEHOLDER):
        data = self.__dict__.get("_data", {})
        if isinstance(data, dict) and name in data:
            return self._iterable_wrapper(data[name])
        elif hasattr(data, name):
            return getattr(data, name)
        elif default is not self._PLACEHOLDER:
            return default
        else:
            raise AttributeError(f"{self.__class__!r} object has no attribute {name!r}")

    def _iterable_wrapper(self, item):
        if not isinstance(item, Iterable) or isinstance(item, (str, bytes)):
            return item
        obs = observable(item)
        obs.add_observer(self._on_change)
        return obs

    def __setattr__(self, key, value):
        if key in self.__dict__:
            super().__setattr__(key, value)
        else:
            self[key] = value

    def _pure_load(self: "YamlFile") -> None:
        data = load(self.path.read_text(encoding="utf-8"), Loader=Loader)
        data = data if data is not None else {}
        data = observable(data)
        data.add_observer(self._on_change)
        self.__dict__["_data"] = data

    def _load(self: "YamlFile") -> None:
        dct = self.__dict__
        try:
            if "_data" not in dct and "parent" not in dct and "path" in dct:
                self._pure_load()
        except FileNotFoundError:
            logger.info(f"Config file {self.path} does not exists. Creating.")
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.touch()
            dct["_data"] = ObservableDict({})
        except YAMLError as e:
            raise YamlFileError(f"File is corrupted {e!r}", self.path) from e
        except IOError as e:
            raise YamlFileError(
                f"Unknown IOError {e!r} while reading file", self.path
            ) from e

    def _dump(self: "YamlFile") -> None:
        dct = self.__dict__
        try:
            if "_parent" in dct:
                return dct["_parent"]._dump()
            self.path.write_text(dump(self._data, Dumper=Dumper), encoding="utf-8")
        except IOError as e:
            raise YamlFileError(f"Unknown IOError {e!r}", self.path) from e

    def _on_change(self, changes):
        self._dump()
