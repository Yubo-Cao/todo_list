import os
import sys

from PySide6 import QtCore
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication

from todo.model import TodoItem, todo_list, todo_list_model
from todo.view.todolistview import TodoListView


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


if __name__ == "__main__":
    os.environ["QT_QUICK_CONTR-OLS_STYLE"] = "Material"
    QtCore.qInstallMessageHandler(qt_message_handler)

    app = QApplication(sys.argv)
    engine = QQmlApplicationEngine()
    engine.load(QUrl("qml/Test.qml"))
    if not engine.rootObjects():
        sys.exit(-1)
    # root = engine.rootObjects()[0]
    # view = TodoListView(todo_list_model)

    if not todo_list:
        todo_list.append(
            TodoItem(
                "Test",
                "This is a test",
            )
        )
    sys.exit(app.exec())
