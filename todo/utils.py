import asyncio
import functools
import inspect
from collections.abc import Callable, Coroutine
from threading import Thread
from typing import Any, Literal, TypeVar, Optional, Union, Type

from todo.log import get_logger

logger = get_logger(__name__, use_config=False)


def splitter(data, pred):
    yes, no = [], []
    for d in data:
        (yes if pred(d) else no).append(d)
    return [yes, no]


def run_async(func, *args, **kwargs):
    if not asyncio.iscoroutinefunction(func):
        raise TypeError("func must be a coroutine function")

    result = []
    exception = []

    async def _impl():
        try:
            result.append(await func(*args, **kwargs))
        except Exception as e:
            exception.append(e)

    t = Thread(target=asyncio.run, args=(_impl(),))
    t.start()
    t.join()
    if exception:
        raise exception[0]
    return result[0]


def sync(func: Callable[..., Coroutine]) -> Callable[..., Any]:
    def _impl(*args, **kwargs):
        return run_async(func, *args, **kwargs)

    return _impl


def sync_cached(func: Callable[..., Coroutine]) -> Callable[..., Any]:
    return functools.cache(sync(func))


C = TypeVar("C")


class Property:
    def __init__(
        self: C,
        func: Callable[[C], Coroutine[None, None, Any]],
        cached=False,
        immutable=False,
    ):
        self.func = func
        self.cached = cached
        self.immutable = immutable
        self.name = func.__name__

    def __get__(self, instance: C, owner) -> Any:
        if instance is None:
            return self
        if self.cached:
            if self.name not in instance.__dict__:
                instance.__dict__[self.name] = run_async(self.func, instance)
            return instance.__dict__[self.name]
        return run_async(self.func, instance)

    def __set__(self, instance: C, value: Any):
        if self.cached and not self.immutable:
            instance.__dict__[self.name] = value
        else:
            raise AttributeError(
                "can't set attribute (only cached properties can be set)"
            )

    def __delete__(self, instance: C):
        raise AttributeError("can't delete attribute")

    def expire(self, instance: C) -> Any:
        if not self.cached:
            raise ValueError("can't expire uncached property")
        instance.__dict__.pop(self.name, None)

    def refresh(self, instance: C) -> Any:
        if not self.cached:
            raise ValueError("can't refresh uncached property")
        instance.__dict__[self.name] = result = run_async(self.func, instance)
        return result

    def __repr__(self):
        return f"<Property {self.name}>"


def sync_property(
    func: Callable[..., Coroutine] = None, **kwargs
) -> Property | Callable[..., Property]:
    if func is None:
        return functools.partial(Property, **kwargs)
    return Property(func, **kwargs)


class ClassInstanceDispatch:
    """
    Provide a decorator to register a function returning different function
    based on whether the callee is a class or an instance.
    """

    def __init__(self, meth):
        self.meth = meth

    @property
    def __func__(self) -> list[Callable]:
        results = [self.meth]
        if (cls_meth := getattr(self, "_class", None)) is not None:
            results.append(cls_meth)
        if (inst_meth := getattr(self, "_instance", None)) is not None:
            results.append(inst_meth)
        return results

    def register(
        self,
        meth: Optional[Callable] = None,
        *,
        kind: Literal["class", "instance"] = "class",
    ) -> Optional[Callable]:
        """
        Register a method to be called when the decorated method is called
        with a class or an instance.

        :param meth: the method to register
        :param kind: the kind of object to register the function for, either
            "class" or "instance"
        :return: none
        """

        if meth is None:
            return functools.partial(self.register, kind=kind)

        if kind not in ("class", "instance"):
            raise ValueError("kind must be either 'class' or 'instance'")

        if kind == "class":
            if hasattr(self, "_class"):
                raise ValueError(
                    f"class function {self.meth.__name__} has already registered"
                )
            self._class = meth
        else:
            if hasattr(self, "_instance"):
                raise ValueError(
                    f"instance function {self.meth.__name__} has already registered"
                )
            self._instance = meth

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        if inspect.isclass(args[0]):
            try:
                return self._class(*args, **kwargs)
            except AttributeError:
                raise ValueError(
                    f"class function {self.meth.__name__} has not registered"
                )
        else:
            try:
                return self._instance(*args, **kwargs)
            except AttributeError:
                raise ValueError(
                    f"instance function {self.meth.__name__} has not registered"
                )

    def __get__(self, instance, owner):
        if instance is None:
            return functools.partial(self, owner)
        return functools.partial(self, instance)

    @staticmethod
    def dispatch(meth) -> "ClassInstanceDispatch":
        """
        This function allows different method to be returned based on whether it is
        access through instance or class.

        :param meth: The stub method to be decorated
        """

        dispatcher = ClassInstanceDispatch(meth)
        return dispatcher

    @staticmethod
    def decorator_dispatch(
        meth: Optional[Callable] = None,
        name: str = "",
        get_instance: Optional[Callable] = None,
    ) -> Union[Callable[..., "ClassInstanceDispatch"], "ClassInstanceDispatch"]:
        """
        This function assumes the method provided is an instance method that decorate
        another method. If the class is used to call this method, it will assume the function
        can extract self from the self of the method it decorates.

        :param meth: The stub method to be decorated
        :param name: The name of the instance
        :param get_instance: The function to extract the instance from the self of the method it decorates
        """

        if meth is None:
            return functools.partial(
                ClassInstanceDispatch.decorator_dispatch,
                name=name,
                get_instance=get_instance,
            )

        if name == "" and get_instance is None:
            logger.warning(
                f"No name nor get_instance provided for decorator dispatch, assuming {meth.__name__}"
            )
            name = meth.__name__

        def _get_instance(self):
            try:
                return getattr(self, name)
            except AttributeError:
                raise ValueError(f"Self does not have {name} attribute")

        get_instance = get_instance or _get_instance

        dispatcher = ClassInstanceDispatch(meth)
        dispatcher.register(meth, kind="instance")

        @functools.wraps(meth)
        def _impl(cl, fn, *args, **kwargs):
            if inspect.iscoroutinefunction(fn):

                async def _deco(self, *fn_args, **fn_kwargs):
                    return await meth(get_instance(self), fn, *args, **kwargs)(
                        self, *fn_args, **fn_kwargs
                    )

            else:

                def _deco(self, *fn_args, **fn_kwargs):
                    return meth(get_instance(self), fn, *args, **kwargs)(
                        self, *fn_args, **fn_kwargs
                    )

            return _deco

        dispatcher.register(_impl, kind="class")
        return dispatcher

    @staticmethod
    def get_self(meth, *args, **kwargs):
        """
        Try to extract self in the argument.

        :param meth: the method
        :param args: arguments for the method
        :param kwargs: keyword arguments for the method
        :return: self in the argument
        """

        if (
            inspect.ismethod(meth)
            and (self := getattr(meth, "__self__", None)) is not None
        ):
            return self
        sign = inspect.signature(meth)
        name = "self"
        if name not in sign.parameters:
            logger.warning(
                f"The method {meth.__name__} has unconventional name for self."
            )
            name = next(iter(sign.parameters))
        try:
            ba = sign.bind(*args, **kwargs)
        except ValueError:
            logger.warning("Incomplete parameters. Fallback to bind_partial.")
            try:
                ba = sign.bind_partial(*args, **kwargs)
            except ValueError:
                raise ValueError("Invalid parameters, failed to extract self.")
        ba.apply_defaults()
        try:
            return ba.arguments[name]
        except KeyError:
            raise ValueError("Unable to extract self from the arguments provided.")


T = TypeVar("T")


def find_kv(dicts: list[T], k: str, v: Any, dicts_description: str = "") -> Optional[T]:
    """
    Find the first dictionary in the list that has the key and value.

    :param dicts: the list of dictionaries, or objects with expected attributes.
    :param k: the key to search
    :param v: the value to search
    :param dicts_description: the message to print if the key is not found
    :return: dict or object if found, None otherwise
    """

    for d in dicts:
        if isinstance(d, dict):
            if d.get(k) == v:
                return d
        else:
            if getattr(d, k, None) == v:
                return d
    if dicts_description:
        logger.warning(f"{k}={v} not found in {dicts_description}")
    else:
        logger.warning(f"Could not find {k}={v}.")
    return None


async def execute(fn: Callable, *args, **kwargs):
    """
    Execute a function or a coroutine function.

    :param fn: function or coroutine function
    :param args: the arguments
    :param kwargs: the keyword arguments
    :return: the result of the function
    """

    if asyncio.iscoroutinefunction(fn):
        return await fn(*args, **kwargs)
    else:
        return fn(*args, **kwargs)


def chain_execute(*fn):
    """
    Execute a list of functions or coroutine functions in order.

    :param fn: a list of functions or coroutine functions
    :param args: the arguments
    :param kwargs: the keyword arguments
    :return: the result of the last function
    """

    async def _impl(*args, **kwargs):
        for f in fn:
            await execute(f, *args, **kwargs)

    return _impl


def isfunction(fn: Any) -> bool:
    """
    Check if the object is a function.

    :param fn: the object to check
    :return: True if the object is a function, False otherwise
    """

    return (
        inspect.isfunction(fn) or inspect.ismethod(fn) or inspect.ismethoddescriptor(fn)
    )


def get_functions(fn: Any) -> list[Callable]:
    """
    Get the functions from the object.

    :param fn: the object to check
    :return: list of functions
    """

    if inspect.isfunction(fn):
        return [fn]
    for name in ["__func__", "__funcs__", "__function__", "__functions__", "__call__"]:
        if (f := getattr(fn, name, None)) is not None:
            return get_functions(f)
    logger.warning(f"Unable to get functions from {fn}")
    return []


def singleton(cls):
    """
    Decorator to make a class a Singleton class (only one instance).

    :param cls: the class to decorate
    :return: the decorated class
    """

    instances = {}

    @functools.wraps(cls)
    def _singleton(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return _singleton


T = TypeVar("T")
V = TypeVar("V")

DELEGATE_BLACKLIST = {
    "__class__",
    "__delattr__",
    "__getattribute__",
    "__getattr__",
    "__setattr__",
}

COMMON_DUNDER_METHODS = {
    "__getitem__",
    "__setitem__",
    "__delitem__",
    "__iter__",
    "__len__",
    "__contains__",
    "__reversed__",
    "__eq__",
    "__ne__",
    "__lt__",
    "__le__",
    "__gt__",
    "__ge__",
    "__hash__",
    "__str__",
    "__repr__",
    "__add__",
    "__sub__",
    "__mul__",
    "__truediv__",
    "__floordiv__",
    "__mod__",
    "__divmod__",
    "__pow__",
    "__or__",
    "__and__",
    "__xor__",
    "__enter__",
    "__exit__",
    "__call__",
    "__await__",
    "__aiter__",
    "__anext__",
    "__aenter__",
    "__aexit__",
    "__int__",
    "__bool__",
    "__format__",
}


def delegate(
    cls: Type[T] = None,
    target: Optional[Type[V]] = None,
    instance_getter: Optional[Callable[[T], V]] = None,
    instance_name: Optional[str] = "",
    suppress_log: bool = False,
    enable_setattr: bool = False,
):
    """
    Composition & delegate.

    :param cls: the class that holds the V instance
    :param target: the target class
    :param instance_getter: the function to get the instance of V
    :param instance_name: the name of the instance
    :param suppress_log: suppress the warning if target is not provided
    :param enable_setattr: enable __setattr__
    :return: the decorated class
    """

    if cls is None:
        return functools.partial(
            delegate,
            target=target,
            instance_getter=instance_getter,
            instance_name=instance_name,
            suppress_log=suppress_log,
            enable_setattr=enable_setattr,
        )

    if instance_name == "":
        instance_name = target.__name__.lower()
    if instance_getter is None:

        def instance_getter(self):
            return getattr(self, instance_name)

    def _get_instance(self):
        instance = instance_getter(self)
        if instance is None:
            raise AttributeError(
                f"{self} does not hold an instance of {target}."
            ) from None
        return instance

    def _method(method_name: str):
        def _call(self, *args, **kwargs):
            try:
                method: Callable = getattr(_get_instance(self), method_name)
            except AttributeError:
                raise AttributeError(
                    f"{cls.__name__} has no attribute {method_name}"
                ) from None
            return method(*args, **kwargs)

        return _call

    if target is not None:
        for attribute_name in dir(target):
            attribute = getattr(target, attribute_name)
            if not inspect.isfunction(attribute):
                continue
            if attribute_name in DELEGATE_BLACKLIST:
                continue
            if attribute_name in cls.__dict__:
                continue
            setattr(cls, attribute_name, _method(attribute_name))

    else:
        if not suppress_log:
            logger.warning(
                f"No target class specified for {cls.__name__}. Using dunder methods list."
            )
        for attribute_name in COMMON_DUNDER_METHODS:
            if attribute_name in cls.__dict__:
                continue
            setattr(cls, attribute_name, _method(attribute_name))

        def _getattr(self, name: str):
            return getattr(_get_instance(self), name)

        original_getattr = getattr(cls, "__getattr__", None)
        if original_getattr is None:
            setattr(cls, "__getattr__", _getattr)
        else:

            def _fallback_getattr(self, name: str):
                try:
                    return original_getattr(self, name)
                except AttributeError:
                    return _getattr(self, name)

            setattr(cls, "__getattr__", _fallback_getattr)
    if enable_setattr:

        def _setattr(self, name: str, value: Any):
            try:
                setattr(_get_instance(self), name, value)
            except AttributeError:
                if not suppress_log:
                    # until at least 1 setattr is called, the instance must not exist.
                    logger.debug(f"Unable to set attribute {name} to {value} on {self}")
            super(cls, self).__setattr__(name, value)

        setattr(cls, "__setattr__", _setattr)

    return cls
