import functools
from typing import Mapping, Sequence

import appdirs
from yaml import YAMLError, dump, load

try:
    from yaml import CDumper as Dumper
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader, Dumper

from pathlib import Path
import logging

logger = logging.getLogger("config")
NAME = "grade_checker"
AUTHOR = "Yubo"


class ConfigException(Exception):
    """
    The base class of exception for config module.
    """


class ReadConfigException(ConfigException):
    """
    Denote the exception during reading configuration files.
    """


class WriteConfigException(ConfigException):
    """
    Denote the exception during writing configuration files.
    """


def _load(self) -> None:
    dict = self.__dict__
    try:
        if "_data" not in dict and "parent" not in dict and "path" in dict:
            with open(self.path, "r") as config:
                self._data = load(config, Loader)
                if self._data is None:
                    self._data = generate_default_config(dict)
    except FileNotFoundError as e:
        logger.info('Config file "config.yml" does not exists. Creating.')
        dict["path"].parent.mkdir(parents=True, exist_ok=True)
        dict["path"].touch()
        self._data = generate_default_config(dict)
    except YAMLError as e:
        logger.fatal(f"Config file is corrupted {e!r}")
        raise ReadConfigException(f"Config file is corrupted {e!r}") from e
    except IOError as e:
        logger.fatal(f"Unknown IOError {e!r} while reading config file {self.path}")
        raise ReadConfigException(
            f"Unknown IOError {e!r} while reading config file {self.path}"
        ) from e


def generate_default_config(dict):
    return {
        "grade_checker": {
            "first_time": True,
            "db_path": str(dict["path"].parent / "grade_checker.db"),
            "cookies_path": str(dict["path"].parent / "e-class-cookies.txt"),
            "log_path": str(dict["path"].parent / "logfile.log"),
            "subject_template": "Question about grade",
            "body_template": """
Good {time}, {title} {teacher_last_name},
I have a question about my grade. I don't understand why that my grade has dropped
Thanks for your time and consideration.
Yours sincerely,
{your_name} {period} {class} student
                """.strip(),
            "daemon_interval": 1800 * 100,
            "grade_increase_notification_template": "Your grade of {class} has increased from {old_grade} to {new_grade}.",
            "grade_decrease_notification_template": "Your grade of {class} has dropped from {old_grade} to {new_grade}.\nClick to talk to {title} {teacher_last_name} as necessary.\nDon't feel bad, you are doing good.",
        }
    }


def _ensure_loaded(func):
    @functools.wraps(func)
    def _deco(self, *args, **kwargs):
        _load(self)
        return func(self, *args, **kwargs)

    return _deco


def _dump(self):
    try:
        with open(self.path, "w+") as config:
            config.write(dump(self._data, Dumper=Dumper))
    except AttributeError:
        _dump(self._parent)
    except IOError as e:
        raise WriteConfigException(
            f"Unknown IOError {e!r} while writing config file {self.path}"
        ) from e


def _ensure_dumped(func):
    @functools.wraps(func)
    def _deco(self, *args, **kwargs):
        _load(self)
        res = func(self, *args, **kwargs)
        _dump(self)
        return res

    return _deco


def _iterable_wrapper(self, data):
    if (
        not isinstance(data, str)
        and isinstance(data, Sequence)
        or isinstance(data, Mapping)
    ):
        res = Config(None, _parent=self)
        res._data = data
        return res
    return data


class Config:
    def __init__(
        self,
        path: Path = Path(appdirs.user_config_dir("grade_checker", "Yubo"))
        / "config.yml",
        _parent=None,  # type: Config
    ):
        if path is None and _parent is None:
            raise ValueError("Path must not be None.")
        elif path is not None and _parent is not None:
            raise ValueError("Do not pass any argument for parent.")
        elif path is not None:
            self.path = path
        else:
            self._parent = _parent

    @_ensure_dumped
    def __setitem__(self, key, item):
        self._data[key] = item

    @_ensure_loaded
    def __getitem__(self, key):
        return _iterable_wrapper(self, self._data[key])

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
        return repr(self._data)

    @_ensure_loaded
    def __str__(self):
        return str(self._data)

    @_ensure_loaded
    def __iter__(self):
        return iter(self._data)

    @_ensure_loaded
    def __getattr__(self, name, default=...):
        if (
            res
            if (res := getattr(self.__dict__.get("_data", ...), name, ...)) is not ...
            else (res := self.__dict__.get("_data", ...).get(name, ...)) is not ...
        ):
            if hasattr(res, "__call__"):
                func = res

                @functools.wraps(func)
                def _ensured(*args, **kwargs):
                    res = func(*args, **kwargs)
                    _dump(self)
                    return _iterable_wrapper(self, res)

                return _ensured
            return _iterable_wrapper(self, res)
        elif default is not ...:
            return default
        else:
            raise AttributeError(f"{self.__class__!r} object has no attribute {name!r}")

cfg = Config()
