import QtQuick 2.15
import QtQuick.Controls.Material 2.15
import QtQuick.Layouts 1.15

RoundPane {
    id: control
    property alias name: txt.text
    property alias icon: image.source
    Material.elevation: 6
    radius: 15
    
    RowLayout{
        anchors.fill: parent
        Image {
            id: image
            sourceSize.height: parent.height
        }
        Text {
            id: txt;
        }
    }
}