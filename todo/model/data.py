from collections.abc import Callable
from datetime import datetime
from typing import NamedTuple, Optional

from PIL import Image

from todo.globals import data_path
from todo.model.observables import ObservableList


class TodoItem(NamedTuple):
    """
    Represent a todo item.
    """

    title: str
    completed: bool
    created_date: datetime
    photo: Optional[Image.Image] = None
    description: str = ""
    subtask: list["TodoItem"] = []
    due_date: Optional[datetime] = None


todo_list: ObservableList = ObservableList(data_path / "todo_list.yaml")
