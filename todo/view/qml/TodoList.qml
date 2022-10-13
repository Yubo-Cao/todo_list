import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    objectName: "todoList"

    ColumnLayout {
        anchors {
            fill: parent
            margins: 16
        }

        // header
        RowLayout {
            spacing: 16
            RowLayout {
                spacing: 4
                Text {
                    text: "\ue2e6"
                    font.family: "Material Icons"
                    font.pixelSize: 48
                    color: Material.accent
                }
                Text {
                    text: "Task"
                    font.pointSize: 24
                    color: Material.accent
                }
            }
            Item {
                Layout.fillWidth: true
            }
            Button {
                padding: 16
                Material.background: Material.background
                contentItem: RowLayout {
                    spacing: 4
                    Text {
                        text: "\ue164"
                        font.family: "Material Icons"
                        font.pixelSize: 24
                        color: Material.accent
                        Layout.alignment: Qt.AlignVCenter
                    }
                    Text {
                        text: "Sort"
                        font.pointSize: 16
                        color: Material.accent
                    }
                }
            }
        }

        // real content
        ListView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            model: model
            spacing: 8

            delegate: TodoItem {
                title: model.title
                description: model.description ? model.description : ""
                due_date: model.due_date ? model.due_date : new Date()
                completed: model.completed
                photo: model.photo ? model.photo : "null"
                create_date: model.create_date ? model.create_date : new Date()
                subtasks: model.subtasks ? model.subtasks : undefined
            }
        }
    }

    ListModel {
        objectName: "model"
        id: model
        ListElement {
            title: "Task 1"
            description: "This is a task"
            completed: false
            picture: "https://picsum.photos/200/300"
        }
        ListElement {
            title: "Task 2"
            description: "This is a task"
            completed: false
            picture: "https://picsum.photos/200/300"
        }
    }
}