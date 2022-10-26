import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Dialogs
import QtQuick.Controls.Material 2.15
import QtQuick.Controls.Material.impl 2.15

Rectangle {
    id: root
    property alias source: image.source
    property bool usePlaceholder: true
    width: 200
    height: 200
    radius: 8
    clip: true

    Image {
        id: image
        source: ""
        anchors.centerIn: parent
        fillMode: Image.PreserveAspectCrop
        width: parent.width
        height: parent.height
    }

    Component.onCompleted: {
       if (usePlaceholder && source == "") {
           source = "../../images/placeholder.svg";
       }
    }

    Connections {
        target: root
        function onUsePlaceholderChanged() {
            var placeholder = "../../images/placeholder.svg"
            if (usePlaceholder && source === "") {
                source = placeholder
            }
            if (!usePlaceholder && image.source === placeholder) {
                source = ""
            }
        }
    }
}