import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Dialogs
import QtQuick.Templates as T
import QtQuick.Controls.Material 2.15
import QtQuick.Controls.Material.impl
import QtQuick.Window
import "components"

ApplicationWindow {
    id: root
    visible: true
    width: 640
    height: 480
    title: qsTr("Hello World")

    Frame {
        MEditableParagraph {
            id: text
            text: "Hello World"
            anchors.centerIn: parent
            onTextChanged: {
                console.log(text)
            }
        }
    }
}