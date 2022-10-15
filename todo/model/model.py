from typing import Any

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt
from PySide6.QtGui import QPixmap, QImage

from todo.globals import cache_path
from hashlib import sha256

from todo.model import ObservedCollection
from todo.model.data import todo_list
from todo.model.observed import Notify, Action
from todo.utils import index_range


class TodoListModel(QAbstractListModel):
    ROLES = [b"title", b"description", b"completed", b"photo", b"due_date", b"subtasks", b"created_date"]
    TitleRole, DescriptionRole, CompletedRole, PhotoRole, DueDateRole, SubtasksRole, CreatedDateRole = (Qt.UserRole + i
                                                                                                        for i in range(
        len(ROLES)))

    def __init__(self, *args, todos: ObservedCollection[list], **kwargs):
        super().__init__(*args, **kwargs)
        self._model = todos
        todos.attach(self._on_change)

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._model)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        print("data", index, role)
        if not index.isValid() or index.row() > len(self._model):
            return None
        match role:
            case self.TitleRole | Qt.DisplayRole | Qt.EditRole:
                return self._model[index.row()].title
            case self.DescriptionRole:
                return self._model[index.row()].description
            case self.CompletedRole:
                return self._model[index.row()].completed
            case Qt.DecorationRole | self.PhotoRole:
                img = self._model[index.row()].photo
                sha = sha256(img.tobytes()).hexdigest()
                img.save(path := cache_path / f"{sha}.png")
                return str(path)
            case self.DueDateRole:
                return self._model[index.row()].due_date
            case self.SubtasksRole:
                return self._model[index.row()].subtasks
            case self.CreatedDateRole:
                return self._model[index.row()].created_date
            case _:
                return None

    def roleNames(self) -> dict[int, bytes]:
        return {i: role for i, role in enumerate(self.ROLES)}

    def headerData(
            self, section: int, orientation: Qt.Orientation, role: int = ...
    ) -> Any:
        if role == Qt.DisplayRole:
            return "TodoList"
        return None

    def setData(self, index: QModelIndex, value: Any, role: int = Qt.EditRole) -> bool:
        """Called when the user edits an item"""
        if not index.isValid() or index.row() > len(self._model):
            return False
        match role:
            case Qt.EditRole:
                self._model[index.row()] = value
            case _:
                return False
        return True

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        """Making the items editable"""
        if not index.isValid():
            return Qt.ItemIsEnabled
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable

    def _on_change(self, notify: Notify):
        """Called when the todo_list changes"""
        match notify.action:
            case Action.UPDATE | Action.MOVE:
                begin, end = index_range(notify.index)
                self.dataChanged.emit(begin, end)
            case Action.CREATE:
                self.layoutChanged.emit()


todo_list_model = TodoListModel(todos=todo_list)
