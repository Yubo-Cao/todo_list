from collections.abc import Iterable
from pathlib import Path
from typing import TypeVar, Callable

from yaml import YAMLError, dump, load

from todo.model.observables import ObservableDict, observable, ObservableCollection, ObservableList, ObservableSet
from todo.utils import delegate

try:
    from yaml import CDumper as Dumper
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader, Dumper  # type: ignore

from todo.error import YamlFileError
from todo.log import get_logger

logger = get_logger(__name__, use_config=False)


@delegate(target=ObservableSet, name="data")
@delegate(target=ObservableList, name="data")
@delegate(target=ObservableDict, name="data")
@delegate(target=ObservableCollection, name="data")
class YamlFile:
    def __init__(
            self,
            data: ObservableCollection | Callable[[], ObservableCollection],
            path: Path | str,
    ):
        """
        Provide serialization support for observable collections. If the file does
        not exist, it will be created. You can use file.attr to access the data in the file,
        and file.attr = x to set the value of attr to x.

        :param path: The path to the file.
        :param data: The data to be stored in the file. This is treated as default data if
        the file does not exist.
        """

        self.__dict__["_default_data"] = data if not isinstance(data, ObservableCollection) else lambda: data
        self.__dict__["path"] = Path(path)
        self._load()

    def __repr__(self):
        return f"{self.__class__.__name__}({self.data!r})"

    def __str__(self):
        return str(self.data)

    def __getattr__(self, name):
        data = self.__dict__.get("data")
        if isinstance(data, ObservableDict) and name in data:
            return self._observable_wrapper(data[name])
        raise AttributeError(f"{self.__class__!r} object has no attribute {name!r}")

    T = TypeVar("T")

    def _observable_wrapper(self, data: T) -> ObservableCollection | T:
        """
        Wrap the item if it is an iterable (to collection). If it is an immutable,
        or primary data type, return as is.

        :param data: the data
        :return: the wrapped
        """

        if not isinstance(data, Iterable) or isinstance(data, (str, bytes)):
            return data
        obs = observable(data)
        obs.attach(self._on_change)
        return obs

    def __setattr__(self, key, value):
        if key in self.__dict__:
            super().__setattr__(key, value)
        else:
            self[key] = value

    def _load(self) -> None:
        """
        Load the data. If the data is empty, create a file and save as specified
        in the default_data.
        """

        dct = self.__dict__
        try:
            data = load(self.path.read_text(encoding="utf-8"), Loader=Loader) or self._default_data()
            dct["data"] = data
        except FileNotFoundError:
            logger.info(f"YAML file {self.path} does not exists. Creating.")
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.touch()
            dct["data"] = self._default_data()
            self._dump()
        except YAMLError as e:
            raise YamlFileError(f"File is corrupted {e!r}", self.path) from e
        except IOError as e:
            raise YamlFileError(
                f"Unknown IOError {e!r} while reading file", self.path
            ) from e

    def _dump(self: "YamlFile") -> None:
        try:
            self.path.write_text(dump(self.data, Dumper=Dumper), encoding="utf-8")
        except IOError as e:
            raise YamlFileError(f"Unknown IOError {e!r}", self.path) from e

    def _on_change(self, _):
        self._dump()
