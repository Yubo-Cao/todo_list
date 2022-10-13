from typing import Any

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt
from PySide6.QtGui import QPixmap, QImage

from todo.model import ObservedCollection
from todo.model.data import todo_list
from todo.model.observed import Notify, Action
from todo.utils import index_range


class TodoListModel(QAbstractListModel):
    def __init__(self, *args, todos: ObservedCollection[list], **kwargs):
        super().__init__(*args, **kwargs)
        self.todos = todos
        todos.attach(self)

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.todos)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        print("data", index, role)
        if not index.isValid() or index.row() > len(self.todos):
            return None
        match role:
            case Qt.DisplayRole | Qt.EditRole:
                return self.todos[index.row()]
            case Qt.DecorationRole:
                img = self.todos[index.row()].photo
                return QPixmap.fromImage(
                    QImage(
                        img.tobytes(),
                        img.width,
                        img.height,
                        img.width * 3,
                        QImage.Format_RGB888,
                    )
                )
            case _:
                return None

    def headerData(
            self, section: int, orientation: Qt.Orientation, role: int = ...
    ) -> Any:
        if role == Qt.DisplayRole:
            return "TodoList"
        return None

    def setData(self, index: QModelIndex, value: Any, role: int = Qt.EditRole) -> bool:
        """Called when the user edits an item"""
        if not index.isValid() or index.row() > len(self.todos):
            return False
        match role:
            case Qt.EditRole:
                self.todos[index.row()] = value
            case _:
                return False
        return True

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        """Making the items editable"""
        if not index.isValid():
            return Qt.ItemIsEnabled
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable

    def __call__(self, notify: Notify):
        """Called when the todo_list changes"""
        match notify.action:
            case Action.UPDATE | Action.MOVE:
                begin, end = index_range(notify.index)
                self.dataChanged.emit(begin, end)
            case Action.CREATE:
                self.layoutChanged.emit()


todo_list_model = TodoListModel(todos=todo_list)
