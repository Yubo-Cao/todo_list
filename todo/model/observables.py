import functools
import warnings
from collections.abc import Iterable, Callable
from typing import Any, Generic, Protocol, TypeVar, cast, Optional

from todo.log import get_logger
from todo.utils import delegate

logger = get_logger(__name__, use_config=False)

T = TypeVar("T")


class Observer(Protocol):
    def __call__(self, index: Any) -> None:
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
    def __init__(self, data: T | "ObservableCollection[T]", parent: Optional["ObservableCollection"] = None) -> None:
        super().__init__(data)
        self._data = data
        self._parent = parent

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__()
        for name, meth in cls.__dict__.items():
            if not callable(meth) or name in {"__init__", "__new__", "__setitem__",
                                              "__getattr__", "to_data", "data"}:
                continue
            wrapper: Callable[[Callable], Callable] = kwargs.get("wrapper", ObservableCollection._observe_wrapper)
            setattr(cls, name, wrapper(meth))

        if _getattr := getattr(cls, "__getattr__", None):
            def _wrap_getattr(self, name: str):
                result = observable(_getattr(self, name), self)
                if isinstance(result, ObservableCollection):
                    return result
                if callable(result):
                    return wrapper(result)
                return result

            setattr(cls, "__getattr__", _wrap_getattr)
        return cls

    def notify(self, index: Any) -> None:
        """Notify all observers of a change. Collection call observer with index"""
        if not (isinstance(index, tuple) and len(index) == 2):
            index = (self._normalize_key(index), self)
        super().notify(index)
        if self._parent:
            self._parent.notify(index)

    @classmethod
    def _observe_wrapper(cls, fn):
        @functools.wraps(fn)
        def wrapper(self, *args, **kwargs):
            obs = observable(fn(self, *args, **kwargs), self)
            return obs

        return wrapper

    T = TypeVar("T")

    @classmethod
    def _normalize_key(cls, index: int | slice | T) -> list[int | T]:
        if isinstance(index, list):
            return index
        if isinstance(index, slice):
            return list(range(index.start or 0, index.stop or 0, index.step or 1))
        return [index]

    def __setitem__(self, key, item):
        self._data[key] = item
        self.notify(key)

    def __getitem__(self, key):
        return self._data[key]

    def __delitem__(self, key):
        del self._data[key]
        self.notify(key)

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
        return self.to_data()

    def to_data(self) -> T:
        """
        Recursively convert an ObservableCollection to pure data
        """

    @property
    def parent(self):
        return self._parent

    @property
    def root(self):
        if self._parent:
            return self._parent.root
        return self


class ObservableList(ObservableCollection[list]):
    """
    Represent an observable list.
    """

    def __init__(self, data: list = None, parent: Optional[ObservableCollection] = None):
        if data is None:
            data = []
        super().__init__(data, parent)

    _PLACEHOLDER = object()

    def append(self, item):
        self._data.append(item)
        self.notify(len(self._data) - 1)

    def remove(self, target):
        for idx, item in enumerate(self._data):
            if item == target:
                self._data.pop(idx)
                self.notify(idx)
                return
        raise ValueError(f"Item {target} not found in list")

    def pop(self, idx: int):
        self._data.pop(idx)
        self.notify(idx)

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
        self.notify(idx)

    def __add__(self, other):
        return self._data + other

    def __mul__(self, other):
        return self._data * other

    def to_data(self) -> T:
        return [item.to_data() if isinstance(item, ObservableCollection) else item for item in self._data]


class ObservableDict(ObservableCollection[dict]):
    """Represents an observable dict"""

    def __init__(self, data: dict = None, parent: Optional[ObservableCollection] = None):
        if data is None:
            data = {}
        super().__init__(data, parent)

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

    def to_data(self) -> T:
        return {key: value.to_data() if isinstance(value, ObservableCollection) else value for key, value in
                self._data.items()}


def _attribute_observe(cls):
    """Wrap a class that returns AttributeObservable instances in an observable"""

    def _fn_wrapper(fn):
        @functools.wraps(fn)
        def _wrapped_func(self, *args, **kwargs):
            obs = observable(fn(self, *args, **kwargs), self)
            return obs if not isinstance(obs, ObservableCollection) else AttributeObservable(obs)

        return _wrapped_func

    def _meth_wrapper(self, meth):
        @functools.wraps(meth)
        def _bound_method(*args, **kwargs):
            obs = observable(meth(*args, **kwargs), self)
            return obs if not isinstance(obs, ObservableCollection) else AttributeObservable(obs)

        return _bound_method

    for attribute_name, fn in cls.__dict__.items():
        if attribute_name in {"__init__", "__new__", "__getattr__", "__setattr__", "__setitem__", "__delitem__"}:
            continue
        if not callable(fn):
            continue
        setattr(cls, attribute_name, _fn_wrapper(fn))

    _getattr = getattr(cls, "__getattr__", None)
    if _getattr is not None:
        def _wrapped_getattr(self, name: str):
            if name in {"notify", "to_data", "data", "parent", "root"}:
                return _getattr(self, name)
            if isinstance(value := observable(_getattr(self, name), self), ObservableCollection):
                return AttributeObservable(value)
            if callable(value):
                return _meth_wrapper(self, value)
            return value

        setattr(cls, "__getattr__", _wrapped_getattr)
    return cls


@_attribute_observe
@delegate(instance_name="_data", target=ObservableCollection)
class AttributeObservable:
    """A decorator for an observable dict that allows to access the dict values as attributes"""

    def __init__(self, data: ObservableCollection | list | set | dict | tuple,
                 parent: Optional[ObservableCollection] = None):
        self.__dict__["_data"] = observable(data, parent or getattr(data, "parent", None))

    def __getattr__(self, item):
        if isinstance(self._data, ObservableDict):
            try:
                return self._data[item]
            except KeyError:
                pass
        raise AttributeError(f"{self.__class__} has no attribute {item}")

    def __repr__(self):
        return f"{self.__class__.__name__}({self._data})"

    def __str__(self):
        return str(self._data)

    def __setattr__(self, key, value):
        if key.startswith("_") or not isinstance(self._data, ObservableDict):
            super().__setattr__(key, value)
        else:
            self._data[key] = value


AttributeObservable = cast(ObservableCollection, AttributeObservable)


class ObservableSet(ObservableCollection[set]):
    """Represents an observable set"""

    def __init__(self, data: set = None, parent: Optional[ObservableCollection] = None):
        if data is None:
            data = set()
        super().__init__(data, parent)

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

    def __getitem__(self, item):
        raise TypeError("ObservableSet does not support indexing")

    def __delitem__(self, key):
        raise TypeError("ObservableSet does not support indexing")

    def __setitem__(self, key, value):
        raise TypeError("ObservableSet does not support indexing")

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

    def to_data(self) -> T:
        return {value.to_data() if isinstance(value, ObservableCollection) else value for value in self._data}


class ObservableTuple(ObservableCollection[tuple]):
    """Represents an observable tuple"""

    def __init__(self, data: tuple = tuple(), parent: Optional[ObservableCollection] = None):
        super().__init__(data, parent)

    def __add__(self, other):
        return self._data + other

    def __mul__(self, other):
        return self._data * other

    def to_data(self) -> T:
        return tuple(value.to_data() if isinstance(value, ObservableCollection) else value for value in self._data)


def observable(data, parent: Optional[ObservableCollection] = None, warning: bool = False) -> Any:
    """
    Make sure data is observed, as much as possible
    :param data: the data to observe
    :param parent: if not None, the data will have this as parent
    :param warning: if True, a warning will be raised if the data is not observed
    """

    if isinstance(data, ObservableCollection):
        data._parent = parent
    if not isinstance(data, Iterable) or isinstance(data, str | bytes):
        return data
    match data:
        case list():
            data = ObservableList(data, parent)
        case dict():
            data = ObservableDict(data, parent)
        case set():
            data = ObservableSet(data, parent)
        case tuple():
            data = ObservableTuple(data, parent)
        case _:
            if warning:
                warnings.warn(f"Data {data} is not observed")
            return data
    return data
