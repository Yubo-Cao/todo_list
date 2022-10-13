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
    }
}