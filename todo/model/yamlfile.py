from collections.abc import Iterable
from pathlib import Path
from typing import TypeVar, Callable

from yaml import YAMLError, dump, load

try:
    from yaml import CDumper as Dumper
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader, Dumper  # type: ignore

from todo.error import YamlFileError
from todo.log import get_logger
from todo.model.observables import (
    ObservableDict,
    observable,
    ObservableCollection,
    ObservableList,
    ObservableSet,
    AttrObservableDict,
)
from todo.utils import delegate

logger = get_logger(__name__, use_config=False)


@delegate(target=ObservableSet, name="_data")
@delegate(target=ObservableList, name="_data")
@delegate(target=ObservableDict, name="_data")
@delegate(target=ObservableCollection, name="_data")
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

        dct = self.__dict__
        dct["_default_data"] = (
            data if not isinstance(data, ObservableCollection) else lambda: data
        )
        dct["path"] = Path(path)
        self._load()

    def __repr__(self):
        return f"{self.__class__.__name__}({self._data!r})"

    def __str__(self):
        return str(self._data)

    def __getattr__(self, name):
        data = self.__dict__.get("_data")
        if data is None:
            raise AttributeError(
                f"{self.__class__.__name__!r} object has no attribute {name!r}"
            )
        try:
            return self._observable_wrapper(data[name])
        except (KeyError, TypeError):
            raise AttributeError(
                f"{self.__class__!r} object has no attribute {name!r}"
            ) from None

    def __setattr__(self, key, value):
        if key in self.__dict__:
            super().__setattr__(key, value)
        else:
            self[key] = value

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
        if isinstance(obs, ObservableDict):
            obs = AttrObservableDict(obs)
        obs.attach(self._on_change)
        return obs

    def _load(self) -> None:
        """
        Load the data. If the data is empty, create a file and save as specified
        in the default_data.
        """

        dct = self.__dict__
        try:
            dct["_data"] = self._observable_wrapper(
                load(self.path.read_text(encoding="utf-8"), Loader=Loader)
                or self._default_data()
            )
        except FileNotFoundError:
            logger.info(f"YAML file {self.path} does not exists. Creating.")
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.touch()
            dct["_data"] = self._observable_wrapper(self._default_data())
            self._dump()
        except YAMLError as e:
            raise YamlFileError(f"File is corrupted {e!r}", self.path) from e
        except IOError as e:
            raise YamlFileError(
                f"Unknown IOError {e!r} while reading file", self.path
            ) from e

    def _dump(self: "YamlFile") -> None:
        try:
            self.path.write_text(
                dump(ObservableCollection.to_data(self._data), Dumper=Dumper),
                encoding="utf-8",
            )
        except IOError as e:
            raise YamlFileError(f"Unknown IOError {e!r}", self.path) from e

    def _on_change(self, _):
        self._dump()
