import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Controls.Material 2.15
import QtQuick.Dialogs

Rectangle {
    id: root
    property string text: ""
    property bool active: false
    property alias font: text_display.font

    implicitWidth: layout.width
    implicitHeight: layout.height
    color: "transparent"

    StackLayout {
        id: layout
        anchors.fill: parent
        currentIndex: active ? 1 : 0

        width: text_display.width

        Text {
            id: text_display
            text: root.text
            font.pointSize: 10
            visible: root.text !== "" && root.visible
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.alignment: Qt.AlignHCenter | Qt.AlignVCenter

            MouseArea {
                anchors.fill: parent
                onClicked: {
                    active = true
                    editor.forceActiveFocus()
                }
            }
        }

        TextField {
            id: editor
            text: root.text
            font.pointSize: text_display.font.pointSize
            visible: root.text === "" && root.visible
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.alignment: Qt.AlignHCenter | Qt.AlignVCenter

            onAccepted: {
                if (editor.text !== root.text) {
                    root.text = editor.text
                }
                active = false
            }
        }
    }

    Keys.onEscapePressed: {
        if (active) {
            active = false
        }
    }

    Shortcut {
        sequence: "Ctrl+Return"
        onActivated: {
            editor.focus = false
            active = false
        }
    }
}