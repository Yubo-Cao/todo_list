import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Component {
    id: root

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
                MIcon {
                    icon: "hamburger"
                    size: 48
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
    }
}