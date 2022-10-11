import inspect
from collections.abc import Callable
from typing import Coroutine, Optional, Any, Literal

from todo.log import get_logger
from todo.utils import ClassInstanceDispatch, execute, sync, chain_execute, isfunction
from . import Spider, SessionManager, Navigator

logger = get_logger(__name__)


class Retry(Spider):
    """
    Implement a chain of responsibility to retry an operation.
    Subclass of this class should implement login/visit/retry function.
    """

    def __init__(self, manager: SessionManager, navigator: Navigator):
        super().__init__(manager, navigator)
        self._next_level = None

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._retry_methods: list[Callable[[], None]] = []
        for name in ["visit", "login", "retry"]:
            if (method := getattr(cls, name, ...)) is not ...:
                if getattr(cls, "_retry_method", ...) is not ...:
                    logger.warning("Retry method already defined, overwriting.")

                cls._retry_methods.append(method)
                break
        else:
            raise ValueError("Class must has method 'visit', 'login', or 'retry'")
        if (method := getattr(cls, "load_nav", ...)) is not ...:
            cls._retry_methods.append(method)
        cls._retry = chain_execute(*cls._retry_methods)
        instance_name = kwargs.get("instance_name", ...) or cls.__name__
        cls.retry = ClassInstanceDispatch.decorator_dispatch(
            Retry.retry, name=instance_name
        )

    def next_level(self, next_level: "Retry") -> None:
        """
        Register the next level of retry.
        """

        self._next_level = next_level

    def retry(
        self,
        need_retry: Any,
        names: Optional[list[str]] = None,
        predicate: Optional[Callable] = None,
    ) -> Callable[..., Coroutine]:
        """
        Retry the operation. A decorator that can be used to retry the
        operation.

        :param need_retry: The function to be retried, or a class with method
        :param names: The names of the functions that should be retried
        :param predicate: The predicate to determine whether the function should be retried
        """

        if inspect.isfunction(need_retry):
            if names or predicate:
                raise ValueError("names and predicate should not be provided")

            async def _retry(
                *args, previous_retried_but_failed_function=None, **kwargs
            ):
                try:
                    return await execute(need_retry, *args, **kwargs)
                except Exception as e:
                    logger.warning(
                        f"{need_retry.__name__} failed {e!r}, {self.__class__.__name__} retrying."
                    )
                    try:
                        await execute(self._retry, self)
                        if previous_retried_but_failed_function:
                            await execute(previous_retried_but_failed_function, self)
                        return await execute(need_retry, *args, **kwargs)
                    except Exception as e:
                        if (nxt := getattr(self, "_next_level", None)) is not None:
                            logger.warning(
                                f"Trying next level {nxt.__class__.__name__}."
                            )
                            return (
                                await nxt.retry(
                                    need_retry,
                                    previous_retried_but_failed_function=self._retry,
                                )
                            )(*args, **kwargs)
                        else:
                            logger.error(f"Failed to retry {need_retry.__name__} {e!r}")
                            await self.close()
                            raise e
                    finally:
                        logger.info(f"Retry {need_retry.__name__} finished.")

            return _retry

        # normalize names, predicate into predicate
        predicate = predicate or (
            (
                lambda x: isfunction(x)
                and not (x.__name__.startswith("__") and x.__name__.endswith("__"))
            )
            if not names
            else (lambda x: x.__name__ in names)
        )
        for name in (
            meth
            for meth in dir(need_retry)
            if predicate(fn := getattr(need_retry, meth, None))
        ):
            need_retry.__dict__[name] = (
                self.retry(fn)
                if inspect.iscoroutinefunction(fn)
                else sync(self.retry(fn))
            )
        return need_retry
