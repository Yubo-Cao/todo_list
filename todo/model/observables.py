import functools
import warnings
from collections.abc import Iterable
from typing import Any, Generic, Protocol, TypeVar, cast

from todo.log import get_logger

logger = get_logger(__name__, use_config=False)

T = TypeVar("T")


class Observer(Protocol):
    def __call__(self, value: Any) -> None:
        """Called when the observed object changes"""


class Observable:
    def __init__(self, value) -> None:
        self._value = value
        self._observers: list[Observer] = []

    def attach(self, obs: list[Observer] | Observer) -> None:
        """Attach an observer to the observable"""
        if isinstance(obs, Iterable):
            [self.attach(o) for o in obs]
            return
        obs = cast(Observer, obs)
        for observer in self._observers:
            if observer == obs:
                warnings.warn("Observer already attached")
                return
        self._observers.append(obs)

    def detach(self, obs: list[Observer] | Observer) -> None:
        """Detach an observer from the observable"""
        if isinstance(obs, Iterable):
            [self.detach(o) for o in obs]
            return
        obs = cast(Observer, obs)
        for observer in self._observers:
            if observer == obs:
                self._observers.remove(obs)
                return
        raise ValueError("Observer not attached")

    def notify(self, value: Any) -> None:
        """Notify all observers of a change"""
        for observer in self._observers:
            observer(value)

    @property
    def observers(self):
        return self._observers


class ObservableCollection(Observable, Generic[T]):
    def __init__(self, data: T | "ObservableCollection[T]") -> None:
        super().__init__(data)
        self._data = data

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        for name, meth in cls.__dict__.items():
            if not callable(meth) or getattr(meth, "__name__", "") in {
                "__init__",
                "__new__",
                "__setitem__",
            }:
                continue

            setattr(cls, name, ObservableCollection._observe_wrapper(meth))
        return cls

    @classmethod
    def _observe_wrapper(cls, fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            return observable(fn(*args, **kwargs))

        return wrapper

    @classmethod
    def _normalize_key(cls, index: int | slice) -> list[int]:
        if isinstance(index, slice):
            return list(range(index.start or 0, index.stop or 0, index.step or 1))
        return [index]

    def __setitem__(self, key, item):
        self._data[key] = item
        self.notify([self._normalize_key(key)])

    def __getitem__(self, key):
        return self._data[key]

    def __delitem__(self, key):
        del self._data[key]
        self.notify([self._normalize_key(key)])

    def __contains__(self, key):
        return key in self._data

    def __len__(self):
        return len(self._data)

    def __repr__(self):
        return f"{type(self).__name__}({self._data!r})"

    def __str__(self):
        return f"{type(self).__name__}({self._data!r})"

    def __eq__(self, other):
        return self._data == other

    def __bool__(self):
        return bool(self._data)

    @property
    def data(self):
        return self._data

    @classmethod
    def to_data(cls, data: "ObservableCollection[T]") -> T:
        """
        Recursively convert an ObservableCollection to pure data
        """

        if isinstance(data, ObservableDict):
            return {k: cls.to_data(v) for k, v in data.items()}
        elif isinstance(data, ObservableList):
            return [cls.to_data(v) for v in data]
        elif isinstance(data, ObservableSet):
            return {cls.to_data(v) for v in data}
        else:
            return data


class ObservableList(ObservableCollection[list]):
    """
    Represent an observable list.
    """

    def __init__(self, data: list):
        super().__init__(data)

    _PLACEHOLDER = object()

    def append(self, item):
        self._data.append(item)
        self.notify([len(self._data) - 1])

    def remove(self, item):
        for idx, item in enumerate(self._data):
            if item == item:
                self._data.pop(idx)
                self.notify([idx])
                return
        raise ValueError(f"Item {item} not found in list")

    def pop(self, idx: int):
        self._data.pop(idx)
        self.notify([idx])

    def extend(self, iterable):
        it = list(iterable)
        self._data.extend(it)
        self.notify(list(range(len(self._data) - len(it), len(self._data))))

    def reverse(self):
        self._data.reverse()
        self.notify(list(range(len(self._data))))

    def clear(self):
        old_len = len(self._data)
        self._data.clear()
        self.notify(list(range(old_len)))

    def sort(self, key=None, reverse=False):
        self._data.sort(key=key, reverse=reverse)
        self.notify(list(range(len(self._data))))

    def insert(self, idx: int, item):
        self._data.insert(idx, item)
        self.notify([idx])

    def __add__(self, other):
        return self._data + other

    def __mul__(self, other):
        return self._data * other


class ObservableDict(ObservableCollection[dict]):
    """Represents an observable dict"""

    def __init__(self, data: dict):
        super().__init__(data)

    _PLACEHOLDER = object()

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def setdefault(self, key: str, default=None):
        # can't in 1 lookup because of notify
        if (result := self._data.get(key, self._PLACEHOLDER)) is self._PLACEHOLDER:
            self._data[key] = default
            self.notify([key])
            return default
        return result

    def pop(self, key: str):
        self._data.pop(key)
        self.notify([key])

    def clear(self):
        old_keys = list(self._data.keys())
        self._data.clear()
        self.notify(old_keys)

    def update(self, other: dict):
        self._data.update(other)
        self.notify(list(other.keys()))

    def popitem(self):
        key, value = self._data.popitem()
        self.notify([key])
        return key, value

    def keys(self):
        return self._data.keys()

    def values(self):
        return self._data.values()

    def items(self):
        return self._data.items()


class AttrObservableDict(ObservableDict):
    """A decorator for an observable dict that allows to access the dict's values as attributes"""

    def __init__(self, data: ObservableDict):
        super().__init__(cast(dict, data))
        if not isinstance(data, ObservableDict):
            raise TypeError("data must be an ObservableDict")
        data.attach(self.notify)

    def __getattr__(self, item):
        try:
            return self._data[item]
        except KeyError:
            raise AttributeError(f"Dict has no attribute {item}")

    def __setattr__(self, key, value):
        if key.startswith("_"):
            super().__setattr__(key, value)
        else:
            self._data[key] = value


class ObservableSet(ObservableCollection[set]):
    """Represents an observable set"""

    def __init__(self, data: set):
        super().__init__(data)

    def add(self, item):
        self._data.add(item)
        self.notify([item])

    def remove(self, item):
        self._data.remove(item)
        self.notify([item])

    def discard(self, item):
        self._data.discard(item)
        self.notify([item])

    def pop(self):
        item = self._data.pop()
        self.notify([item])
        return item

    def clear(self):
        old_items = list(self._data)
        self._data.clear()
        self.notify(old_items)

    def update(self, other: set):
        self._data.update(other)
        self.notify(list(other))

    def __ior__(self, other):
        self.update(other)
        self.notify(list(other))
        return self

    def __or__(self, other):
        if isinstance(other, ObservableSet):
            other = other.data
        return self._data | other

    def __and__(self, other):
        if isinstance(other, ObservableSet):
            other = other.data
        return self._data & other

    def __iand__(self, other):
        self._data &= other
        self.notify(list(other))
        return self


class ObservableTuple(ObservableCollection[tuple]):
    """Represents an observable tuple"""

    def __init__(self, data: tuple):
        super().__init__(data)

    def __add__(self, other):
        return self._data + other

    def __mul__(self, other):
        return self._data * other


def observable(data, warning: bool = False) -> Any:
    """
    Make sure data is observed, as much as possible
    :param data: the data to observe
    :param warning: if True, a warning will be raised if the data is not observed
    """

    if not isinstance(data, Iterable) or isinstance(data, str | bytes) or isinstance(data, Observable):
        return data
    match data:
        case list():
            return ObservableList(data)
        case dict():
            return ObservableDict(data)
        case set():
            return ObservableSet(data)
        case tuple():
            return ObservableTuple(data)
        case _:
            if warning:
                warnings.warn(f"Data {data} is not observed")
            return data
