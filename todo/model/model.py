import dataclasses as dc
import functools
import warnings
from typing import Any, TypeVar

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt, QUrl, QObject
from PySide6.QtGui import QStandardItemModel

from todo.data import *
from todo.model.utils import provide_qt_data, from_qt_data, save_image
from todo.utils import index_range

T = TypeVar('T')


def list_model(data_class: T, flags: Qt.ItemFlags = Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable,
               path_as_image: bool = False):
    """Create a list model for a given data class"""

    fields = [f.name.encode('utf-8') for f in dc.fields(data_class)]
    role2name_dict = {i + Qt.UserRole + 1: name for i, name in enumerate(fields)}
    name2role_dict = {name: i + Qt.UserRole + 1 for i, name in enumerate(fields)}

    def role2name(role):
        """Convert a role to a role name"""
        return role2name_dict[role].decode('utf-8')

    def name2role(name):
        """Get the role for a given name"""
        if isinstance(name, str):
            name = name.encode()
        return name2role_dict[name]

    @provide_qt_data
    def data(self, idx: QModelIndex, role: int = Qt.DisplayRole):
        """Get the data for a given index and role"""
        if not idx.isValid() or idx.row() > len(self._data):
            return None
        row = idx.row()
        try:
            return getattr(self._data[row], role2name(role))
        except AttributeError:
            warnings.warn(f"Unknown role {role}")
            return None

    @from_qt_data
    def set_data(self, idx: QModelIndex, value: Any, role: int = Qt.EditRole) -> bool:
        """Called when the user edits an item"""
        if not idx.isValid() or idx.row() > len(self._data):
            return False
        row = idx.row()
        data = dc.asdict(self._data[row])
        if isinstance(value, Path | QUrl):
            value = save_image(value)
        data[role2name(role)] = value
        self._data[row] = data_class(**data)
        return True

    def header_data(
            self, section: int, orientation: Qt.Orientation, role: int = ...
    ) -> Any:
        if role == Qt.DisplayRole:
            return "TodoList"
        return None

    def get_flags(self, index: QModelIndex) -> Qt.ItemFlags:
        """Making the items editable"""
        if not index.isValid():
            return Qt.ItemIsEnabled
        return flags

    def on_change(self, notify: Notify):
        """Called when the list model changes"""
        match notify.action:
            case Action.UPDATE | Action.MOVE:
                begin, end = index_range(notify.index)
                for row in range(begin, end + 1):
                    self.dataChanged.emit(self.index(row), self.index(row))
            case Action.CREATE | Action.DELETE:
                self.layoutChanged.emit()

    def row_count(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._data)

    def role_names(self) -> dict[int, bytes]:
        return role2name_dict

    def __init__(self, data: ObservedCollection[list[T]], *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        self._data = data
        data.attach(functools.partial(on_change, self))

    return type(
        f"{data_class.__name__}Model",
        (QAbstractListModel,),
        {
            "rowCount": row_count,
            "data": data,
            "setData": set_data,
            "headerData": header_data,
            "flags": get_flags,
            "roleNames": role_names,
            "__init__": __init__,
        },
    )


TodoModel = list_model(TodoItem, path_as_image=True)
NoteModel = list_model(NoteItem, path_as_image=True)
