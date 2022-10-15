import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Dialogs
import QtQuick.Controls.Material 2.15

Item {
    id: root
    property string source: ""
    property int elevation: 1
    property bool usePlaceholder: false

    FileDialog {
        id: fileDialog
        nameFilters: ["*.png", "*.jpg", "*.jpeg", "*.bmp", "*.gif"]
        onAccepted: root.source = selectedFile
    }

    Button {
        id: button

        Material.elevation: elevation
        Material.background: Material.background
        padding: 0
        width: root.width
        height: root.width

        contentItem: MImage {
            id: image
            usePlaceholder: root.usePlaceholder
            source: root.source
            anchors.fill: parent
            width: root.width
            height: root.width
        }

        onClicked: {
            fileDialog.open()
        }
    }

    Connections {
        target: root
        function onSourceChanged() {
            image.source = root.source
        }
    }
}