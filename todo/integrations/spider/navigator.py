import re
from functools import cached_property
from typing import Optional

import yaml
from yaml import Loader, Dumper
from yarl import URL

from todo.log import get_logger
from todo.model.config import config

logger = get_logger(__name__)


class Navigator:
    _navigators: dict[str, "Navigator"] = {}
    _internal_placeholder = "INTERNAL_PLACEHOLDER"

    def __new__(
            cls,
            name: str = "",
            url: URL | str = "",
            children: Optional[list["Navigator"]] = None,
            parent: Optional["Navigator"] = None,
    ):
        if name == cls._internal_placeholder:
            return super().__new__(cls)
        elif parent is None and (nav := cls._navigators.get(name)):
            return nav
        elif parent is None:
            # try to load it
            try:
                logger.info(f"Find navigator {name} in file. Loading...")
                directory = config.paths.navigators / name
                result = Navigator.load(
                    yaml.load(directory.read_text(encoding="utf-8"), Loader=Loader),
                )
                cls._navigators[name] = result
                return result
            except IOError:
                logger.info(f"Navigator {name} not found. Creating new one.")
            # failed, create a new one
            result = super().__new__(cls)
            cls._navigators[name] = result
            return result
        else:
            return super().__new__(cls)

    def __init__(
            self,
            name: str,
            url: URL | str,
            children: Optional[list["Navigator"]] = None,
            parent: Optional["Navigator"] = None,
    ):
        """
        A class to represent a website and its children.

        :param name: the name of the website
        :param url: the url of the website
        :param children: other websites that are hyperlinked to this one, default []
        :param parent: the website that hyperlinks to this one, default is None
        """

        name = self.clean_name(name)
        url = URL(url)
        if parent is not None and not url.is_absolute():
            url = parent.url.join(url)
        if children is None:
            children = []
        self.__dict__.update(
            {
                "name": name,
                "url": url,
                "children": children,
                "parent": parent,
            }
        )

    def __repr__(self):
        return f"Navigator({self.name}, {self.url}, {self.children}, {self.parent})"

    def __str__(self):
        return self.name

    def __iter__(self):
        return iter(self.children)

    @cached_property
    def _lookup_table(self) -> dict[str, "Navigator"]:
        """
        A cached table of dict[str, Navigator] for fast lookup.
        """
        dct = self.__dict__
        if "_lookup_table" not in dct:
            dct["_lookup_table"] = {child.name: child for child in self.children}
        return self._lookup_table

    def _refresh(self):
        """
        Refresh the lookup table.
        """

        self.__dict__.pop("_lookup_table", None)

    _NO_DEFAULT = object()

    def get(self, item: str | int, default: "Navigator" = _NO_DEFAULT) -> "Navigator":
        """
        Get a direct child by name.

        :param item: the name of the child or the index of the child
        :param default: the default value if not found
        :return: the child
        """

        try:
            if isinstance(item, int):
                return self.children[item]
            else:
                return self._lookup_table[item]
        except (KeyError, IndexError):
            if default is self._NO_DEFAULT:
                raise ValueError(f"Navigator {item} not found.") from None
            return default

    def __getitem__(self, item):
        return self.get(item)

    def __getattr__(self, item):
        try:
            return self.get(item)
        except ValueError:
            raise AttributeError(
                f"'{self.__class__.__name__}' object has no attribute '{item}'"
            )

    def __setitem__(self, key, value):
        nav = Navigator(key, value, parent=self)
        if (old := self._lookup_table.get(key)) is not None:
            logger.warning(f"Navigator {key} already exists. Old is overwritten.")
            self.children.remove(old)
        self.children.append(nav)
        self._refresh()

    def __setattr__(self, key, value):
        if key in self.__dict__:
            super().__setattr__(key, value)
        else:
            self[key] = value

    @staticmethod
    def clean_name(name: str):
        """
        Clean the name of the navigator.
        """

        name = name.strip().lower()
        name = re.sub(r"\s+", "_", name)
        if name == "children":
            raise ValueError("Navigator name cannot be 'children'.")
        return name

    def __contains__(self, item):
        return (
                item in self.children
                or item in self._lookup_table
                or any(item in child for child in self.children)
        )

    def __len__(self):
        return len(self.children)

    @classmethod
    def load(cls, dct: dict[str, str | dict[str, str]] | str) -> "Navigator":
        """
        Load a navigator from a dict.

        :param dct: the dict to load from
        :return: the navigator
        """

        if isinstance(dct, str):
            dct = yaml.load(config.paths.navigators / dct, Loader=Loader)
        if not isinstance(dct, dict):
            raise TypeError(f"Cannot load navigator from {dct}")

        nav = cls.__new__(cls, cls._internal_placeholder)
        for name, value in dct.items():
            if name == "children":
                nav.__dict__["children"] = [cls.load(child) for child in value]
            else:
                nav.__init__(name, value)
        return nav

    def dump(self) -> dict[str, str | list[dict]]:
        """
        Dump the data from the navigator.

        :return: the data
        """

        if self.children:
            return {
                self.name: str(self.url),
                "children": [child.dump() for child in self.children],
            }
        else:
            return {self.name: str(self.url)}

    def save(self):
        """
        Save the navigator to a file.
        """

        file = config.paths.navigators / self.name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(yaml.dump(self.dump(), Dumper=Dumper), encoding="utf-8")

    def find(self, name: str) -> "Navigator":
        """
        Find a child by name.

        :param name: the name of the child
        :return: the child
        """

        name = self.clean_name(name)
        if name in self._lookup_table:
            return self[name]
        else:
            for child in self.children:
                if name in child:
                    return child.find(name)
            raise ValueError(f"Navigator {name} not found.")

    def path_to(self, name: str) -> list["Navigator"]:
        """
        Find the path to a child by name.

        :param name: the name of the child
        :return: the path
        """

        name = self.clean_name(name)
        if name in self:
            return []
        else:
            for child in self.children:
                if name in child:
                    return [] + child.path_to(name)
            raise ValueError(f"Navigator {name} not found.")

    @property
    def root(self):
        """
        The root navigator.
        """

        if self.parent is None:
            return self
        else:
            return self.parent.root

    def add_all(self, dct: dict[str, str] | list[tuple[str, str]]):
        """
        Add all children from a dict or list of tuples.

        :param dct: the dict or list of tuples
        """

        if isinstance(dct, dict):
            dct = dct.items()
        for name, url in dct:
            self[name] = url

    def print(self, indent: int = 0, indent_width: int = 4):
        """
        Print the navigator.

        :param indent: the indent level
        :param indent_width: the indent width
        """

        print(" " * indent + self.name)
        for child in self.children:
            child.print(indent + indent_width)

    def __eq__(self, other):
        if isinstance(other, Navigator):
            return self.dump() == other.dump()
        else:
            return False
