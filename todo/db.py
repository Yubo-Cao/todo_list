import atexit
import sqlite3
from cmath import isnan
from collections.abc import Callable, Iterator
from numbers import Number
from typing import Any, Iterable, get_type_hints

from todo.log import logger
from todo.model.config import config

connection = sqlite3.connect(
    config.paths.db,
    check_same_thread=False,
    isolation_level=None,
)


def _place_holder(cls, *args, **kwargs) -> str:
    raise NotImplemented


class Field:
    # It's a descriptor that allows you to define a field in a class that will be used to create a column
    # in a database table
    _supported_types: dict[Callable, str] = {
        int: "INTEGER",
        float: "REAL",
        str: "TEXT",
        bool: "INTEGER",  # SQLite does not have a boolean type
    }

    def __init__(
        self,
        name: str = "",
        constructor: Callable = _place_holder,
        column_type: str = "",
        unique: bool = True,
        not_null: bool = True,
        primary_key: bool = False,
    ) -> None:
        if not callable(constructor) or isinstance(constructor, type(None)):
            raise TypeError("{name!r} type hint must be callable")
        self._name = f"{self.__class__.__name__}-{name}"
        self.name = name
        self.constructor = constructor
        try:
            self.column_type = column_type or self._supported_types[constructor]
        except KeyError:
            raise TypeError(f"{name!r} type is not supported")
        self.unique = unique
        self.not_null = not_null
        self.primary_key = primary_key

    def __set__(self, instance: Any, value: Any) -> None:
        if value is ...:
            value = self.constructor()
        else:
            try:
                value = self.constructor(
                    value
                )  # if constructor does not complain, we accept it as a valid type
            except (TypeError, ValueError) as e:
                type_name = self.constructor.__name__
                msg = f"{value!r} is not compatible with {self.name}:{type_name}"
                raise TypeError(msg) from e
            if self.not_null:
                if value is None or (isinstance(value, Number) and isnan(value)):
                    raise ValueError(f"{self.name} cannot be None")
        instance.__dict__[self._name] = value

    def __set_name__(self, owner: Any, name: str):
        self.name = name
        self._name = f"{self.__class__.__name__}-{name}"

    def __get__(self, instance: Any, owner: Any) -> Any:
        if instance is None:
            return self
        else:
            return instance.__dict__[self._name]

    def __repr__(self) -> str:
        return f"{self.name} {self.column_type}{' NOT NULL' if self.not_null else ''}{' PRIMARY KEY' if self.primary_key else ''}"


class Model:
    # It's a class that creates a table in a SQLite database with the same name as the class, and the
    # columns are the fields of the class.
    # All the instances, when created will be saved in the database.

    @classmethod
    def _fields(cls) -> dict[str, type]:
        return get_type_hints(cls)

    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        for name, constructor in cls._fields().items():
            setattr(cls, name, Field(name, constructor))
        setattr(
            cls,
            "__slots__",
            tuple(
                name for name, value in cls.__dict__.items() if isinstance(value, Field)
            ),
        )
        cursor = connection.cursor()
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS {}({}, UNIQUE({}))".format(
                getattr(cls, "table_name", None) or cls.__name__.lower(),
                ", ".join(f"{cls.__dict__[field]}" for field in cls.__slots__),
                ", ".join(
                    field for field in cls.__slots__ if cls.__dict__[field].unique
                ),
            )
        )
        cursor.close()

    def __init__(self, *args, **kwargs) -> None:
        attrs = dict(zip(self.__slots__, args))
        attrs.update(kwargs)
        cls = self.__class__
        for k in cls.__slots__:
            cls.__dict__[k].__set__(self, attrs.get(k, ...))
        cursor = connection.cursor()
        fields_names, fields, values = (
            cls.__slots__,
            [cls.__dict__[f] for f in cls.__slots__],
            tuple(self),
        )
        table = cls.__dict__.get("table_name", cls.__name__.lower())

        # use primary keys to update or insert
        primary_keys, non_primary_keys = getattr(cls, "primary_keys", None), getattr(
            cls, "non_primary_keys", None
        )
        # cache values of primary keys
        if primary_keys is None:
            primary_keys, non_primary_keys = [], []
            for field in fields:
                if field.primary_key:
                    primary_keys.append(field.name)
                else:
                    non_primary_keys.append(field.name)
            cls.primary_keys, cls.non_primary_keys = primary_keys, non_primary_keys

        if primary_keys:
            if not cursor.execute(
                "UPDATE {} SET {} WHERE {}".format(
                    table,
                    ", ".join(
                        f"{field}=?"
                        for field in fields_names
                        if not cls.__dict__[field].primary_key
                    ),
                    " AND ".join(f"{pk}=?" for pk in primary_keys),
                ),
                (
                    *(getattr(self, npk) for npk in non_primary_keys),
                    *(getattr(self, pk) for pk in primary_keys),
                ),
            ).rowcount:
                # if not updated, it does not exists yet, so we insert
                cls._insert(cursor, fields_names, values, table)
        else:
            # otherwise, we use all the unique fields to update the row
            unique_fields, non_unique_fields = getattr(
                cls, "unique_fields", None
            ), getattr(cls, "non_unique_fields", None)

            # cache the values of the unique fields
            if unique_fields is None:
                unique_fields, non_unique_fields = [], []
                for field in fields:
                    if field.unique:
                        unique_fields.append(field)
                    else:
                        non_unique_fields.append(field)
                    cls.unique_fields, cls.non_unique_fields = (
                        unique_fields,
                        non_unique_fields,
                    )
            if non_unique_fields:  # only update the non-unique fields
                if not cursor.execute(
                    "UPDATE {} SET {} WHERE {}".format(
                        table,
                        ", ".join(f"{field.name}=?" for field in non_unique_fields),
                        " AND ".join(f"{field.name}=?" for field in unique_fields),
                    ),
                    tuple(getattr(self, field.name) for field in non_unique_fields)
                    + tuple(getattr(self, field.name) for field in unique_fields),
                ).rowcount:
                    cls._insert(cursor, fields_names, values, table)
            else:  # otherwise, just do all of them and see if it exists
                if (
                    cursor.execute(
                        "SELECT COUNT(*) FROM {} WHERE {}".format(
                            table,
                            " AND ".join(f"{field.name}=?" for field in unique_fields),
                        ),
                        tuple(getattr(self, field.name) for field in unique_fields),
                    ).fetchone()[0]
                    == 0
                ):
                    cls._insert(cursor, fields_names, values, table)
        cursor.close()

    @classmethod
    def _insert(cls, cursor, fields_names, values, table):
        try:
            cursor.execute(
                "INSERT INTO {} ({}) VALUES({})".format(
                    table,
                    ", ".join(fields_names),
                    ", ".join("?" for _ in values),
                ),
                values,
            )
        except sqlite3.IntegrityError as e:
            logger.error(
                f"Insert failed {e!r} for {', '.join(f'{k}={v}' for k, v in zip(fields_names, values))}"
            )

    def __iter__(self) -> Iterator[Any]:
        return (getattr(self, name) for name in self.__slots__)

    def __repr__(self) -> str:
        values = ", ".join(
            f"{name}={value!r}" for name, value in self._asdict().items()
        )
        cls_name = self.__class__.__name__
        return f"{cls_name}({values})"

    def __setattr__(self, name: str, value: Any) -> None:
        object.__setattr__(self, name, value)
        cls = self.__class__
        as_dict = self._asdict()
        value = as_dict.pop(name)
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE {} SET {}=? WHERE {}".format(
                getattr(cls, "table_name", None) or cls.__name__.lower(),
                name,
                " AND ".join(f"{field}=?" for field in as_dict),
            ),
            (
                value,
                *as_dict.values(),
            ),
        )
        cursor.close()

    def _asdict(self) -> dict[str, Any]:
        return dict(zip(self.__class__.__slots__, self))

    def exists(self, excludes: str | Iterable[str] = []) -> bool:
        as_dict = self._parse_excludes(excludes)
        cursor = connection.cursor()
        cls = self.__class__
        table = getattr(cls, "table_name", None) or cls.__name__.lower()
        result = bool(
            cursor.execute(
                "SELECT COUNT(*) FROM {} WHERE {}".format(
                    table,
                    " AND ".join(f"{field}=?" for field in as_dict),
                ),
                tuple(as_dict.values()),
            ).fetchall()
        )
        cursor.close()
        return result

    @classmethod
    def _from_db(cls, *args):
        attrs = dict(zip(cls.__slots__, args))
        attrs = {
            k: v if v is not None else Model.HANDLE_NONE[getattr(cls, k).constructor]
            for k, v in attrs.items()
        }
        return cls(**attrs)

    @classmethod
    def find(cls, *args, **kwargs):
        restrictions = cls._parse_restrictions(args, kwargs)
        table = getattr(cls, "table_name", None) or cls.__name__.lower()

        cursor = connection.cursor()
        return [
            cls(*data)
            for data in cursor.execute(
                "SELECT {} FROM {} WHERE {}".format(
                    ", ".join(cls.__slots__),
                    table,
                    " AND ".join(f"{field}=?" for field in restrictions)
                    if restrictions
                    else "1=1",
                ),
                tuple(restrictions.values()),
            ).fetchall()
        ]

    @classmethod
    def find_one(cls, *args, **kwargs):
        cursor = connection.cursor()
        restrictions = cls._parse_restrictions(args, kwargs)
        table = getattr(cls, "table_name", None) or cls.__name__.lower()
        result = cursor.execute(
            "SELECT {} FROM {} WHERE {} LIMIT 1".format(
                ", ".join(cls.__slots__),
                table,
                " AND ".join(f"{field}=?" for field in restrictions)
                if restrictions
                else "1=1",
            ),
            tuple(restrictions.values()),
        ).fetchone()
        if not result:
            msg = f"No {cls.__name__} found with {', '.join(f'{k}={v}' for k, v in restrictions.items())}"
            logger.error(msg)
            raise ValueError(msg)
        return cls(*result)

    def delete(self, excludes: str | Iterable[str] = []) -> None:
        as_dict = self._parse_excludes(excludes)
        cursor = connection.cursor()
        cls = self.__class__
        cursor.execute(
            "DELETE FROM {} WHERE {}".format(
                getattr(cls, "table_name", None) or cls.__name__.lower(),
                " AND ".join(f"{field}=?" for field in as_dict),
            ),
            tuple(as_dict.values()),
        ).fetchall()
        cursor.close()

    def _parse_excludes(self, exclude):
        if isinstance(exclude, str):
            exclude = exclude.replace(" ", ",").split(",")
        as_dict = self._asdict()
        for e in exclude:
            try:
                as_dict.pop(e)
            except KeyError:
                raise ValueError(f"{e!r} is not a valid field")
        return as_dict

    def __len__(self):
        return len(self.__class__.__slots__)

    @classmethod
    def len(cls):
        cursor = connection.cursor()
        result = cursor.execute(
            "SELECT COUNT(1) FROM {}".format(
                getattr(cls, "table_name", None) or cls.__name__.lower()
            )
        ).fetchone()[0]
        return result

    def __eq__(self, other):
        return isinstance(other, type(self)) and tuple(self) == tuple(other)

    def __hash__(self):
        return hash(tuple(self))

    @classmethod
    def _parse_restrictions(cls, args, kwargs):
        restrictions = dict(zip(cls.__slots__, args))
        for k, v in kwargs.items():
            if k in cls.__slots__:
                restrictions[k] = v
            else:
                raise ValueError(f"{k} is not a valid field")
        return restrictions


class Teacher(Model):
    id = Field(constructor=str, column_type="TEXT", primary_key=True)
    email: str
    name: str


class Grade(Model):
    ts: int
    grade = Field(constructor=float, column_type="REAL", unique=False)
    course_id: str


class Course(Model):
    id = Field(constructor=str, column_type="TEXT", primary_key=True)
    semester: int
    year: int
    period: int
    name: str
    room: str
    teacher_id: str


class Navigation(Model):
    name: str
    url: str


class Grade_Change(Model):
    ts: int
    old_grade: int
    new_grade: float
    course_id: str


# Add trigger for grade_change
cursor = connection.cursor()
cursor.execute(
    """CREATE TRIGGER IF NOT EXISTS on_grade_change AFTER 
    UPDATE ON grade WHEN old.grade <> new.grade 
    BEGIN 
        INSERT INTO
            grade_change (ts, old_grade, new_grade, course_id)
        VALUES
            (
                strftime('%s','now'),
                old.grade,
                new.grade,
                old.course_id
            );
    END;"""
)
cursor.close()

atexit.register(connection.close)
