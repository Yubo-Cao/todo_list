import QtQuick 2.15
import QtQuick.Controls.Material 2.15
import QtQuick.Layouts 1.15
import QtQuick.Controls.Material.impl 2.15

Rectangle {
    property string icon: "menu";
    property int iconSize: 24;
    width: iconSize
    height: iconSize
    color: "transparent"
    property var iconColor: "white"

    property var onClicked: function() {}
    property var onDoubleClicked: function() {}
    property var onWheel: function() {}
    property var onEntered: function() {}
    property var onExited: function() {}

    MouseArea {
        id: control
        anchors.fill: parent
        hoverEnabled: true
        onClicked: {
            parent.onClicked();
        }
        onDoubleClicked: {
            parent.onDoubleClicked();
        }
        onWheel: {
            parent.onWheel();
        }
        onEntered: {
            parent.onEntered();
        }
        onExited: {
            parent.onExited();
        }
    }

    Text {
        anchors.centerIn: parent
        text: parent.icon
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        font.pixelSize: iconSize
        color: iconColor
        font.family: "Material Icons"
    }

    Ripple {
        id: ripple
        clipRadius: 0
        width: parent.width
        height: parent.height
        pressed: control.pressed
        anchor: control
        active: control.containsMouse
        color: control.flat && control.highlighted ?  control.Material.highlightedRippleColor : control.Material.rippleColor
    }
}