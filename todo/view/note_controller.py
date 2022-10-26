from PySide6 import QtCore, QtGui
from todo.data import NoteItem, note_list


class NotesController(QtCore.QObject):
    def __init__(self):
        super().__init__()

    @QtCore.Slot()
    def add(self):
        note_list.append(NoteItem("New Note"))

    @QtCore.Slot(int)
    def delete(self, index):
        note_list.pop(index)
