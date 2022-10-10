import functools
import inspect
from collections.abc import Callable, Iterable

from todo.log import get_logger
from . import SessionManager, Navigator
from ...utils import execute, isfunction, get_functions

logger = get_logger(__name__)


class Spider:
    """
    Generic spider.
    """

    def __init_subclass__(cls, **kwargs):
        """
        Initialize the subclass. Adding factory method: create

        :param kwargs: Keyword arguments.
        """

        # a list of callables to be executed in create factory method
        hooks: list[Callable] = []

        if (methods := kwargs.get("hooks", ...)) is not ...:
            if not isinstance(methods, Iterable):
                raise TypeError("hooks must be an iterable")
            for meth in methods:
                if not isinstance(meth, Callable):
                    raise TypeError("hook must be callable")
            hooks.extend(methods)

        if (fn := cls.__dict__.get("create")) is not None and fn is not Spider.create:
            logger.warning(f"Class {cls.__name__} already has a method named 'create'.")
            hooks.append(fn)
        for name in ["visit", "login", "load_nav"]:
            if (fn := getattr(cls, name, None)) is not None:
                hooks.append(fn)

        init = cls.__init__

        @functools.wraps(init)
        async def create(cl, *create_args, **create_kwargs):
            """
            Create a spider with all the hooks executed.
            """

            logger.debug(f"Creating spider {cls.__name__}")
            self = cl.__new__(cl)
            init(self, *create_args, **create_kwargs)
            for hook in hooks:
                await execute(hook, self)
            return self

        cls.create = classmethod(create)

    @classmethod
    def create(cls, *args, **kwargs):
        """
        Create a spider
        """

    def __init__(self, manager: SessionManager, navigator: Navigator):
        """
        Initialize the spiders. Hooks will not be executed.

        :param manager: Session manager.
        :param navigator: Navigator.
        """

        self.manager = manager
        self.nav = navigator

    async def close(self):
        """
        Close the spider.
        """
        await self.manager.close()
        self.manager.cookie_pool.dump()
        self.nav.save()
