from PySide6.QtQuickWidgets import QQuickWidget

from todo.model import TodoListModel


class TodoListView(QQuickWidget):
    def __init__(self, model: TodoListModel):
        super().__init__()
        self.setSource("./qml/TodoListView.qml")
        self.model = model

    @property
    def model(self) -> TodoListModel:
        return self._model

    @model.setter
    def model(self, model: TodoListModel):
        self._model = model
        self.rootContext().setContextProperty("model", self._model)
