from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, cast

from todo.globals import data_path
from todo.data import YamlFileObserver, ObservedList


@dataclass(frozen=True)
class TodoItem:
    """
    Represent a todo item.
    """

    title: str
    description: str = ""
    completed: bool = False
    photo: Optional[Path] = None
    due_date: Optional[datetime] = None
    created_date: datetime = field(default_factory=datetime.now)


todo_list: ObservedList = cast(ObservedList, YamlFileObserver([], data_path / "todo_list.yaml").to_observable())


@dataclass(frozen=True)
class NoteItem:
    """
    Represents the notes
    """

    text: str = ""
    photo: Optional[Path] = None


note_list: ObservedList = cast(ObservedList, YamlFileObserver([], data_path / "note_list.yaml").to_observable())
