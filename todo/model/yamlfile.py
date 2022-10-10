import functools
import logging
from pathlib import Path
from typing import Mapping, Sequence, Optional

from yaml import YAMLError, dump, load
try:
    from yaml import CDumper as Dumper
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader, Dumper

from todo.error import YamlFileException

logger = logging.getLogger(__name__)


def _ensure_loaded(func):
    @functools.wraps(func)
    def _deco(self: "YamlFile", *args, **kwargs):
        self._load()
        return func(self, *args, **kwargs)

    return _deco


def _ensure_dumped(func):
    @functools.wraps(func)
    def _deco(self: "YamlFile", *args, **kwargs):
        self._load()
        res = func(self, *args, **kwargs)
        self._dump()
        return res

    return _deco


class YamlFile:
    def __init__(
            self,
            path: Path,
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
            self.path = Path(path)
        else:
            self._parent = _parent

    @_ensure_dumped
    def __setitem__(self, key, item):
        self._data[key] = item

    @_ensure_loaded
    def __getitem__(self, key):
        return self._iterable_wrapper(self._data[key])

    @_ensure_dumped
    def __delitem__(self, key):
        del self._data[key]

    @_ensure_loaded
    def __contains__(self, key):
        return key in self._data

    @_ensure_loaded
    def __len__(self):
        return len(self._data)

    @_ensure_loaded
    def __repr__(self):
        return f"{self.__class__.__name__}({self._data!r})"

    @_ensure_loaded
    def __str__(self):
        return str(self._data)

    @_ensure_loaded
    def __iter__(self):
        return iter(self._data)

    @_ensure_loaded
    def __getattr__(self, name, default=...):
        if (
                result
                if (result := getattr(self.__dict__.get("_data", ...), name, ...)) is not ...
                else (result := self.__dict__.get("_data", ...).get(name, ...)) is not ...
        ):
            if hasattr(result, "__call__"):
                func = result

                @functools.wraps(func)
                def _ensured(*args, **kwargs):
                    res = func(*args, **kwargs)
                    self._dump()
                    return self._iterable_wrapper(res)

                return _ensured
            return self._iterable_wrapper(result)
        elif default is not ...:
            return default
        else:
            raise AttributeError(f"{self.__class__!r} object has no attribute {name!r}")

    def _load(self: "YamlFile") -> None:
        dct = self.__dict__
        try:
            if "_data" not in dct and "parent" not in dct and "path" in dct:
                self._data = load(self.path.read_text(encoding='utf-8'), Loader)
                self._data = self._data or {}
        except FileNotFoundError:
            logger.info(f'Config file {self.path} does not exists. Creating.')
            dct["path"].parent.mkdir(parents=True, exist_ok=True)
            dct["path"].touch()
            self._data = self._data or {}
        except YAMLError as e:
            raise YamlFileException(f"File is corrupted {e!r}", self.path) from e
        except IOError as e:
            raise YamlFileException(f"Unknown IOError {e!r} while reading file", self.path) from e

    def _dump(self: "YamlFile") -> None:
        try:
            self.path.write_text(dump(self._data, Dumper=Dumper), encoding='utf-8')
        except AttributeError:
            self._parent._dump()
        except IOError as e:
            raise YamlFileException(f"Unknown IOError {e!r}", self.path) from e

    def _iterable_wrapper(self, data):
        if (
                not isinstance(data, str)
                and isinstance(data, Sequence)
                or isinstance(data, Mapping)
        ):
            # this is intentional
            res = YamlFile(None, _parent=self)  # type: ignore
            res._data = data
            return res
        return data
