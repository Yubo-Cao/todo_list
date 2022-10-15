import QtQuick 2.15
import QtQuick.Controls.Material 2.15
import QtQuick.Layouts 1.15

Item {
    id: root
    property string icon: "missing"
    property int size: 24
    property color color: Material.accent
    property color background: "transparent"
    property int radius: 0
    property int margin: 4
    width: size + margin * 2
    height: size + margin * 2


    Text {
        anchors.centerIn: root

        text: root.icon
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        font.pixelSize: root.size
        color: root.color
        font.family: "Material Icons"
    }

    Rectangle {
        anchors.centerIn: root

        z: -1
        width: root.size + root.margin * 2
        height: root.size + root.margin * 2
        color: root.background
        radius: root.radius
    }

    FontLoader { source: "../../fonts/MaterialIcons-Regular.ttf" }
}