import os
import sys
from datetime import datetime

from PySide6 import QtCore
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from todo.model import TodoItem, todo_list, todo_list_model


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
    os.environ["QT_QUICK_CONTROLS_STYLE"] = "Material"
    QtCore.qInstallMessageHandler(qt_message_handler)
    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()
    qml_filename = os.path.join(os.path.dirname(__file__), "qml/Test.qml")
    engine.load(QtCore.QUrl.fromLocalFile(qml_filename))
    if not engine.rootObjects():
        sys.exit(-1)
    engine.rootObjects()[0].setProperty("model", todo_list_model)
    todo_list.append(
        TodoItem(
            "Test",
            "This is a test",
        )
    )
    sys.exit(app.exec())
