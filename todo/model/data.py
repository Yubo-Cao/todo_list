from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from PIL import Image

from todo.globals import data_path
from todo.model import YamlFileObserver
from todo.model.observed import ObservedList, ObservedCollection


@dataclass(frozen=True)
class TodoItem:
    """
    Represent a todo item.
    """

    title: str
    description: str = ""
    completed: bool = False
    photo: Optional[Image.Image] = None
    due_date: Optional[datetime] = None
    subtasks: list["TodoItem"] = field(default_factory=list)
    created_date: datetime = field(default_factory=datetime.now)


todo_list: ObservedCollection[list] = YamlFileObserver([], data_path / "todo_list.yaml").to_observable()
