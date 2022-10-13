import functools
import warnings
from collections.abc import Iterable, Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any, Generic, Protocol, TypeVar, cast, Optional, Hashable, Literal, Union

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


class Action(Enum):
    """The action that was performed on the collection"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    READ = "read"
    MOVE = "move"


ALL = object()
Index = Union[list[Union[int, slice, Hashable]], Literal[ALL], list[Literal[ALL]]]


@dataclass(init=False)
class Notify(Generic[T]):
    """A change to an observable collection"""

    action: Action
    index: Optional[Index]
    value: Optional[list[Any]]
    observed: "ObservedCollection"

    def __init__(self, type: Action | str, index: Optional[Index], value: Optional[list[Any]],
                 collection: "ObservedCollection"):
        self.action = Action(type)
        self.index = Notify._normalize_index(index)
        self.value = value
        self.observed = collection

    @staticmethod
    def _normalize_index(index: Any) -> Index:
        if index is ALL:
            return [ALL]
        if isinstance(index, slice | int | Hashable):
            return [index]
        if isinstance(index, Iterable):
            return list(index)
        raise TypeError(f"Invalid index type: {Action(index)}")


class ObservedCollection(Observable, Generic[T]):
    def __init__(self, data: T | "ObservedCollection[T]", parent: Optional["ObservedCollection"] = None) -> None:
        super().__init__(data)
        self._data = data
        self._parent = parent

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__()
        for name, meth in cls.__dict__.items():
            if not callable(meth) or name in {"__init__", "__new__", "__setitem__",
                                              "__getattr__", "to_data", "data"}:
                continue
            wrapper: Callable[[Callable], Callable] = kwargs.get("wrapper", ObservedCollection._observe_wrapper)
            setattr(cls, name, wrapper(meth))

        if _getattr := getattr(cls, "__getattr__", None):
            def _wrap_getattr(self, name: str):
                result = observable(_getattr(self, name), self)
                if isinstance(result, ObservedCollection):
                    return result
                if callable(result):
                    return wrapper(result)
                return result

            setattr(cls, "__getattr__", _wrap_getattr)
        return cls

    def notify(self, index: Notify) -> None:
        """Notify all observers of a change. Collection call observer with index"""
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

    def __setitem__(self, key, item):
        self._data[key] = item
        self.notify(Notify(Action.UPDATE, [key], [item], self))

    def __getitem__(self, key):
        self.notify(Notify(Action.READ, [key], [result := self._data[key]], self))
        return result

    def __delitem__(self, key):
        result = None
        try:
            result = self._data.pop(key)
        except AttributeError:
            del self._data[key]
        self.notify(Notify(Action.DELETE, [key], result, self))

    def __contains__(self, key):
        self.notify(Notify(Action.READ, [key], [result := key in self._data], self))
        return result

    def __len__(self):
        self.notify(Notify(Action.READ, ALL, [result := len(self._data)], self))
        return result

    def __repr__(self):
        # prevent infinite recursion
        self.notify(Notify(Action.READ, ALL, None, self))
        return f"{type(self).__name__}({self._data!r})"

    def __str__(self):
        # prevent infinite recursion
        self.notify(Notify(Action.READ, ALL, None, self))
        return str(self._data)

    def __eq__(self, other):
        self.notify(Notify(Action.READ, ALL, [result := self._data == other], self))
        return result

    def __bool__(self):
        self.notify(Notify(Action.READ, ALL, [result := bool(self._data)], self))
        return result

    @property
    def data(self):
        self.notify(Notify(Action.READ, ALL, [result := self.to_data()], self))
        return result

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


class ObservedList(ObservedCollection[list]):
    """
    Represent an observable list.
    """

    def __init__(self, data: list = None, parent: Optional[ObservedCollection] = None):
        if data is None:
            data = []
        super().__init__(data, parent)

    _PLACEHOLDER = object()

    def append(self, item):
        self._data.append(item)
        self.notify(Notify(Action.CREATE, [len(self._data) - 1], [item], self))

    def remove(self, target):
        for idx, item in enumerate(self._data):
            if item == target:
                self.notify(Notify(Action.DELETE, [idx], [self._data.pop(idx)], self))
                return
        raise ValueError(f"Item {target} not found in list")

    def pop(self, idx: int):
        self.notify(Notify(Action.DELETE, [idx], [self._data.pop(idx)], self))

    def extend(self, iterable):
        it = list(iterable)
        self._data.extend(it)
        self.notify(Notify(Action.CREATE, [slice(len(self._data) - len(it), len(self._data))], it, self))

    def reverse(self):
        self._data.reverse()
        self.notify(Notify(Action.MOVE, ALL, self._data, self))

    def clear(self):
        self._data.clear()
        self.notify(Notify(Action.DELETE, ALL, None, self))

    def sort(self, key=None, reverse=False):
        self._data.sort(key=key, reverse=reverse)
        self.notify(Notify(Action.MOVE, ALL, self._data, self))

    def insert(self, idx: int, item):
        self._data.insert(idx, item)
        self.notify(Notify(Action.CREATE, [idx], [item], self))

    def __add__(self, other):
        return self._data + other

    def __mul__(self, other):
        return self._data * other

    def to_data(self) -> T:
        return [item.to_data() if isinstance(item, ObservedCollection) else item for item in self._data]


class ObservedDict(ObservedCollection[dict]):
    """Represents an observable dict"""

    def __init__(self, data: dict = None, parent: Optional[ObservedCollection] = None):
        if data is None:
            data = {}
        super().__init__(data, parent)

    _PLACEHOLDER = object()

    def get(self, key: str, default=None):
        self.notify(Notify(Action.READ, [key], [result := self._data.get(key, default)], self))
        return result

    def setdefault(self, key: str, default=None):
        # can't in 1 lookup because of notify
        if (result := self.get(key, self._PLACEHOLDER)) is self._PLACEHOLDER:
            self._data[key] = default
            self.notify(Notify(Action.CREATE, [key], [default], self))
            return default
        return result

    def pop(self, key: str):
        self.notify(Notify(Action.DELETE, [key], [result := self._data.pop(key)], self))
        return result

    def clear(self):
        self._data.clear()
        self.notify(Notify(Action.DELETE, ALL, None, self))

    def update(self, other: dict):
        other_keys = set(other.keys())
        self_keys = set(self._data.keys())
        updates = other_keys & self_keys
        creates = other_keys - self_keys
        self._data.update(other)  # C is way faster than python
        if updates:
            self.notify(Notify(Action.UPDATE, updates, [other[key] for key in updates], self))
        if creates:
            self.notify(Notify(Action.CREATE, creates, [other[key] for key in creates], self))

    def popitem(self):
        key, value = self._data.popitem()
        self.notify(Notify(Action.DELETE, [key], [value], self))
        return key, value

    def keys(self):
        self.notify(Notify(Action.READ, ALL, [self._data.keys()], self))
        return self._data.keys()

    def values(self):
        self.notify(Notify(Action.READ, ALL, [self._data.values()], self))
        return self._data.values()

    def items(self):
        self.notify(Notify(Action.READ, ALL, [self._data.items()], self))
        return self._data.items()

    def to_data(self) -> T:
        return {key: value.to_data() if isinstance(value, ObservedCollection) else value for key, value in
                self._data.items()}


def _attribute_observe(cls):
    """Wrap a class that returns AttributeObservable instances in an observable"""

    def _fn_wrapper(fn):
        @functools.wraps(fn)
        def _wrapped_func(self, *args, **kwargs):
            obs = observable(fn(self, *args, **kwargs), self)
            return obs if not isinstance(obs, ObservedCollection) else ObservedDot(obs)

        return _wrapped_func

    def _meth_wrapper(self, meth):
        @functools.wraps(meth)
        def _bound_method(*args, **kwargs):
            obs = observable(meth(*args, **kwargs), self)
            return obs if not isinstance(obs, ObservedCollection) else ObservedDot(obs)

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
            if isinstance(value := observable(_getattr(self, name), self), ObservedCollection):
                return ObservedDot(value)
            if callable(value):
                return _meth_wrapper(self, value)
            return value

        setattr(cls, "__getattr__", _wrapped_getattr)
    return cls


@_attribute_observe
@delegate(instance_name="_data", target=ObservedCollection)
class ObservedDot:
    """A decorator for an observable dict that allows to access the dict values as attributes"""

    def __init__(self, data: ObservedCollection | list | set | dict | tuple,
                 parent: Optional[ObservedCollection] = None):
        self.__dict__["_data"] = observable(data, parent or getattr(data, "parent", None))

    def __getattr__(self, item):
        if isinstance(self._data, ObservedDict):
            try:
                return self._data[item]
            except KeyError:
                pass
        raise AttributeError(f"{self.__class__} has no attribute {item}")

    def __setattr__(self, key, value):
        if key.startswith("_") or not isinstance(self._data, ObservedDict):
            super().__setattr__(key, value)
        else:
            self._data[key] = value


ObservedDot = cast(ObservedCollection, ObservedDot)


class ObservedSet(ObservedCollection[set]):
    """Represents an observable set"""

    def __init__(self, data: set = None, parent: Optional[ObservedCollection] = None):
        if data is None:
            data = set()
        super().__init__(data, parent)

    def add(self, item):
        self._data.add(item)
        self.notify(Notify(Action.CREATE, [item], None, self))

    def remove(self, item):
        self._data.remove(item)
        self.notify(Notify(Action.DELETE, [item], None, self))

    def discard(self, item):
        self._data.discard(item)
        self.notify(Notify(Action.DELETE, [item], None, self))

    def pop(self):
        self.notify(Notify(Action.DELETE, [result := self._data.pop()], None, self))
        return result

    def clear(self):
        self._data.clear()
        self.notify(Notify(Action.DELETE, ALL, None, self))

    def update(self, other: set):
        updates = self._data & other
        self._data.update(other)
        self.notify(Notify(Action.UPDATE, updates, None, self))

    def __getitem__(self, item):
        raise TypeError("ObservableSet does not support indexing")

    def __delitem__(self, key):
        raise TypeError("ObservableSet does not support indexing")

    def __setitem__(self, key, value):
        raise TypeError("ObservableSet does not support indexing")

    def __ior__(self, other):
        self.update(other)
        self.notify(Notify(Action.UPDATE, ALL, None, self))
        return self

    def __or__(self, other):
        self.notify(Notify(Action.READ, ALL, [result := (self._data | other)], self))
        return result

    def __and__(self, other):
        self.notify(Notify(Action.READ, ALL, [result := (self._data & other)], self))
        return result

    def __iand__(self, other):
        self._data &= other
        self.notify(Notify(Action.UPDATE, ALL, None, self))
        return self

    def to_data(self) -> T:
        return {value.to_data() if isinstance(value, ObservedCollection) else value for value in self._data}


class ObservedTuple(ObservedCollection[tuple]):
    """Represents an observable tuple"""

    def __init__(self, data: tuple = tuple(), parent: Optional[ObservedCollection] = None):
        super().__init__(data, parent)

    def __add__(self, other):
        return self._data + other

    def __mul__(self, other):
        return self._data * other

    def to_data(self) -> T:
        return tuple(value.to_data() if isinstance(value, ObservedCollection) else value for value in self._data)


def observable(data, parent: Optional[ObservedCollection] = None, warning: bool = False) -> Any:
    """
    Make sure data is observed, as much as possible
    :param data: the data to observe
    :param parent: if not None, the data will have this as parent
    :param warning: if True, a warning will be raised if the data is not observed
    """

    if isinstance(data, ObservedCollection):
        data._parent = parent
    if not isinstance(data, Iterable) or isinstance(data, str | bytes):
        return data
    match data:
        case list():
            data = ObservedList(data, parent)
        case dict():
            data = ObservedDict(data, parent)
        case set():
            data = ObservedSet(data, parent)
        case tuple():
            data = ObservedTuple(data, parent)
        case _:
            if warning:
                warnings.warn(f"Data {data} is not observed")
            return data
    return data
