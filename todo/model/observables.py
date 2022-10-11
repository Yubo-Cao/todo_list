import functools
from collections.abc import Iterable
from typing import Any, Generic, Protocol, TypeVar, cast

from todo.log import get_logger
from todo.utils import delegate

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
                logger.warning("Observer already attached")
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
            return wrap_observable(fn(*args, **kwargs))

        return wrapper

    def __setitem__(self, key, item):
        self._data[key] = item
        self.notify([key])

    def __getitem__(self, key):
        return self._data[key]

    def __delitem__(self, key):
        del self._data[key]
        self.notify([key])

    def __contains__(self, key):
        return key in self._data

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return iter(self._data)

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

    def remove(self, trgt):
        for idx, item in enumerate(self._data):
            if item == trgt:
                self._data.pop(idx)
                self.notify([idx])
                return
        raise ValueError(f"Item {trgt} not found in list")

    def __setitem__(self, key: int | slice, value):
        self._data[key] = value

        match key:
            case int():
                self.notify([key])
            case slice():
                self.notify(list(range(key.start, key.stop, key.step)))

    def __getitem__(self, key: int | slice):
        return self._data[key]

    def __iter__(self):
        return iter(self._data)

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

    def __eq__(self, other):
        return self._data == other

    def __add__(self, other):
        return self._data + other

    def __mul__(self, other):
        return self._data * other

    def __len__(self):
        return len(self._data)

    def __contains__(self, item):
        return item in self._data


class ObservableDict(ObservableCollection[dict]):
    """Represents an observable dict"""

    def __init__(self, data: dict):
        super().__init__(data)

    _PLACEHOLDER = object()

    def __setitem__(self, key: str, value):
        self._data[key] = value
        self.notify([key])

    def __getitem__(self, key: str):
        return self._data[key]

    def __delitem__(self, key: str):
        self._data.pop(key)
        self.notify([key])

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

    def setdefault(self, key: str, default=None):
        self._data.setdefault(key, default)
        self.notify([key])

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

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def __contains__(self, item):
        return item in self._data


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

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def __contains__(self, item):
        return item in self._data


def observable(data) -> Observable:
    """Returns an observable version of data"""
    if isinstance(data, Observable):
        return data
    match data:
        case list():
            return ObservableList(data)
        case dict():
            return ObservableDict(data)
        case set():
            return ObservableSet(data)
        case _:
            raise TypeError(f"Cannot make {type(data)} observable")


def wrap_observable(data) -> Any:
    """Make sure data is observed, as much as possible"""

    if not isinstance(data, Iterable) or isinstance(data, str | bytes):
        return data
    if isinstance(data, Observable):
        return data
    match data:
        case list():
            return ObservableList(data)
        case dict():
            return AttrObservableDict(ObservableDict(data))
        case set():
            return ObservableSet(data)
        case tuple():
            return tuple(wrap_observable(item) for item in data)
        case _:
            return data
