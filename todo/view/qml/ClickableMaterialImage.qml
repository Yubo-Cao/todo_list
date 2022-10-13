import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Controls.Material 2.15
import QtQuick.Controls.Material.impl 2.15

Rectangle {
    id: root
    property string photo: "../assets/placeholder.svg"
    width: 200
    height: 200
    property var onClicked: function() {}

    Image {
        id: image
        source: photo
        anchors.centerIn: parent
        width: root.width
        height: root.height

        visible: photo !== null && photo !== "null" && photo !== ""
        fillMode: Image.PreserveAspectCrop

        Component.onCompleted: {
            if (photo === null || photo === "null" || photo === "") {
                photo = "../assets/placeholder.svg"
            }
        }

        Ripple {
            id: ripple
            clipRadius: Math.max(root.radius, 0.1)
            width: parent.width
            height: parent.height
            pressed: control.pressed
            anchor: control
            active: control.containsMouse
            color: control.flat && control.highlighted ?  control.Material.highlightedRippleColor : control.Material.rippleColor
        }
        MouseArea {
            id: control
            anchors.fill: parent
            hoverEnabled: true
            onEntered: {
                cursorShape = Qt.PointingHandCursor
            }
            onClicked: {
                root.onClicked()
            }
        }
    }
}