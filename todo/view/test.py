import os
import sys
from dataclasses import dataclass

from PySide6 import QtCore
from PySide6.QtCore import QUrl, QObject
from PySide6.QtGui import QStandardItemModel, Qt
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication

from todo.data import todo_list, TodoItem, ObservedList, note_list
from todo.model import TodoModel, NoteModel, list_model
from note_controller import NotesController


def qt_message_handler(mode, context, message):
    if mode == QtCore.QtInfoMsg:
        mode = "Info"
    elif mode == QtCore.QtWarningMsg:
        mode = "Warning"
    elif mode == QtCore.QtCriticalMsg:
        mode = "critical"
    elif mode == QtCore.QtFatalMsg:
        mode = "fatal"
    else:
        mode = "Debug"
    print(
        "%s: %s (%s:%d, %s)" % (mode, message, context.file, context.line, context.file)
    )


@dataclass(frozen=True)
class NavigationItem:
    """
    Represents an item in the navigation drawer. This model is put
    out here, because it's strong coupled to the navigation drawer.
    """

    title: str
    icon: str
    source: str
    item_model: QStandardItemModel = None
    item_controller: QObject = None


navigation_list: ObservedList = ObservedList()
NavigationModel = list_model(NavigationItem, Qt.ItemIsEnabled | Qt.ItemIsSelectable)

if __name__ == "__main__":
    os.environ["QT_QUICK_CONTR-OLS_STYLE"] = "Material"
    QtCore.qInstallMessageHandler(qt_message_handler)

    app = QApplication(sys.argv)
    engine = QQmlApplicationEngine()
    engine.load(QUrl("qml/Main.qml"))
    # failed to load qml/Main.qml
    if not engine.rootObjects():
        sys.exit(-1)

    # Create the navigation model
    navigation_model = NavigationModel(navigation_list)
    # Create the todo model
    todo_model = TodoModel(todo_list)
    # Create the note model
    note_model = NoteModel(note_list)
    # Create the note controller
    note_controller = NotesController()
    # Add the navigation items
    navigation_list.extend(
        [
            NavigationItem("Todo", "list", "Todos.qml", todo_model),
            NavigationItem("Notes", "note", "Notes.qml", note_model, note_controller),
            NavigationItem("Extensions", "extension", "Extensions.qml"),
            NavigationItem("Settings", "settings", "Settings.qml"),
        ]
    )
    # Set the context properties
    engine.rootContext().setContextProperty("navigationModel", navigation_model)

    if not todo_list:
        todo_list.append(TodoItem(
            title="Test",
            description="This is a test",
        ))
    sys.exit(app.exec())
