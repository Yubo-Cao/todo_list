import inspect
import warnings
from collections.abc import Callable, Coroutine
from typing import Optional

import aiohttp

from todo.integrations.spider.cookie_pool import CookiePool
from todo.log import get_logger
from todo.utils import ClassInstanceDispatch

logger = get_logger(__name__)


class SessionManager:
    managers = []
    _session_managers: dict[str, "SessionManager"] = {}

    def __new__(cls, name: str = "default"):
        if (manager := cls._session_managers.get(name)) is None:
            manager = super().__new__(cls)
            cls._session_managers[name] = manager
        return manager

    def __init__(
        self,
        name: str = "default",
        session: Optional[aiohttp.ClientSession] = None,
        cookie_pool: Optional[CookiePool] = None,
    ):
        """
        Initialize the session manager.

        :param name: the name of the session manager.
        :param session: the session to be managed.
        :param cookie_pool: the cookie pool to be used.
        """
        self._session = session
        self.name = name
        self.managers.append(self)
        if cookie_pool is None:
            cookie_pool = CookiePool(name)
        self.cookie_pool = cookie_pool
        self.jar = None

    async def session(self) -> aiohttp.ClientSession:
        """
        Get the session.
        :return: The session.
        """

        if self._session is None:
            self.jar = jar = self.cookie_pool.get_cookie()
            if jar is None:
                jar = aiohttp.CookieJar()
                self.cookie_pool.add_cookie(jar)
            self._session = aiohttp.ClientSession(cookie_jar=jar)
        return self._session

    async def close(self) -> None:
        """
        Close the session.
        :return: None
        """
        if self._session is not None and not self._session.closed:
            await self._session.close()
            self._session = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    @ClassInstanceDispatch.decorator_dispatch(name="manager")
    def supply(self, fn: Callable[..., Coroutine]) -> callable:
        """
        A decorator to supply the session to the function.
        - if calling from SessionManager, it assumes the function is a method,
        and has 'self' argument that contains attribute 'manager', and it will
        call 'manager.supply_session(fn)'.
        - if calling from instance of SessionManager, it supplies the session
        of itself.

        :fn: The function to be decorated.
        :return: The decorated function with session supplied.
        """

        sign = inspect.signature(fn)
        if "session" not in sign.parameters:
            raise TypeError("The function must have a parameter named 'session'.")

        async def wrapper(*args, **kwargs):
            ba = sign.bind_partial(*args, **kwargs)
            ba.apply_defaults()
            if "session" in ba.arguments and ba.arguments["session"] is not None:
                warnings.warn("The function already has a parameter named 'session'.")
            ba.arguments["session"] = await self.session()
            return await fn(*ba.args, **ba.kwargs)

        return wrapper

    def __repr__(self):
        return f"SessionManager({self.name})"
