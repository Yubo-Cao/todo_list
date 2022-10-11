import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    property var model

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
                onClicked: {
                    console.log("clicked")
                }
                padding: 8
                Material.background: Material.background

                Row {
                    spacing: 4
                    anchors {
                        margins: 8
                        centerIn: parent
                    }

                    Text {
                        text: "\ue164"
                        font.family: "Material Icons"
                        font.pixelSize: 24
                        color: Material.accent
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

            delegate: TodoItem {
                title: title
                description: description
                dueDate: dueDate
                createDate: createDate
                completed: completed
                picture: picture
            }
        }
    }
}