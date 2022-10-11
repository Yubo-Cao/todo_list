import shutil
from functools import cached_property
from typing import Optional

import aiohttp

from todo.log import get_logger
from todo.model.config import config

logger = get_logger(__name__)


class CookiePool:
    def __init__(self, name: str):
        self._cookie_index = 0
        self.cookies = []
        self.name = name
        self.path = config.paths.cookies / name
        self.path.mkdir(parents=True, exist_ok=True)
        self.cookies = [
            (c := aiohttp.CookieJar()).load(path) or c
            for path in self.path.glob("*.cookies")
        ]
        self._to_be_saved = []

    def get_cookie(self) -> Optional[aiohttp.CookieJar]:
        """
        Return a cookie jar.
        :return: cookie jar
        """
        if len(self) == 0:
            logger.warning("Cookie pool is empty.")
            return None
        if self._cookie_index >= len(self.cookies):
            logger.info("Cookie pool exhausted, refreshing.")
            self._cookie_index = 0
        cookie = self.cookies[self._cookie_index]
        self._cookie_index += 1
        return cookie

    def add_cookie(self, cookie: aiohttp.CookieJar):
        """
        Add a cookie jar to the pool.
        :param cookie: cookie jar
        """
        if not isinstance(cookie, aiohttp.CookieJar):
            raise TypeError("cookie must be a CookieJar")

        for idx, c in enumerate(self.cookies):
            if c is cookie:
                logger.warning("Cookie already exists.")
                self._to_be_saved.append(idx)
                self.cookies[idx] = cookie
                return

        self.cookies.append(cookie)
        self._to_be_saved.append(len(self) - 1)

    def remove_cookie(self, cookie: Optional[aiohttp.CookieJar | int] = None):
        """
        Remove a cookie jar from the pool.
        :param cookie: cookie jar or cookie index. If not specified, remove the last cookie.
        """
        if cookie is None:
            cookie = len(self.cookies) - 1
        elif isinstance(cookie, aiohttp.CookieJar):
            for idx, c in enumerate(self.cookies):
                if c is cookie:
                    cookie = idx
                    break
        self.cookies.pop(cookie)
        self._to_be_saved.append(-cookie)
        for idx in range(cookie, len(self.cookies)):
            shutil.move(
                self.path / f"{idx + 1}.cookies",
                self.path / f"{idx}.cookies",
            )

    def dump(self):
        """
        Dump the cookie pool.
        """

        for idx in self._to_be_saved:
            if idx < 0:
                (self.path / f"{-idx}.cookies").unlink()
            else:
                self.cookies[idx].save(self.path / f"{idx}.cookies")

    def refresh(self):
        """
        Refresh the cookie pool.
        """
        self.__dict__.pop("cookies", None)

    def __getitem__(self, item):
        return self.cookies[item]

    def __len__(self):
        return len(self.cookies)
