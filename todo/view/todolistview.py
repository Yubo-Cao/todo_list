import sys

from PySide6.QtWidgets import QApplication, QVBoxLayout, QMainWindow
from PySide6.QtWidgets import QListView

from todo.model import todo_list_model, todo_list, TodoItem


def main():
    app = QApplication(sys.argv)
    window = QMainWindow()
    window.setWindowTitle("Todo App")
    layout = QVBoxLayout()
    view = QListView()
    view.setModel(todo_list_model)
    todo_list.append(TodoItem("Test", None, "Test", False, [], None, None, None))
    layout.addWidget(view)
    window.setLayout(layout)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
