import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Controls.Material 2.15
import QtQuick.Controls.Material.impl 2.15

Item {
    id: root
    property var target: root.parent
    anchors.fill: parent

    property int radius: 5

    property var onClicked: function() {}
    property var onDoubleClicked: function() {}
    property var onWheel: function() {}
    property var onEntered: function() {}
    property var onExited: function() {}

    MouseArea {
        id: control
        anchors.fill: parent
        propagateComposedEvents: true
        hoverEnabled: true
        onEntered: function () {
            cursorShape = Qt.PointingHandCursor
            root.onEntered()
        }
        onClicked: function () {
            root.onClicked()
        }
    }

    Ripple {
        id: ripple

        clipRadius: Math.max(root.radius, 0.1)
        anchor: control
        anchors.fill: control
        pressed: control.pressed
        active: control.containsMouse
        color: control.Material.rippleColor
    }

    Component.onCompleted: {
        if (target.radius !== undefined) {
            root.radius = target.radius
            ripple.radius = target.radius
        }
        if (target.onClicked !== undefined) {
            root.onClicked = target.onClicked
        }
    }
}

