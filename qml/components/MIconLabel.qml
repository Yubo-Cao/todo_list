import QtQuick 2.15
import QtQuick.Controls.Material 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root

    property int spacing: -1
    property string direction: "left"

    property string icon: ""
    property bool is_img: false
    property int icon_size: 24
    property int text_size: 14
    property string text: ""
    property string font: "Roboto"
    property color color: "black"
    property color icon_color: "black"
    property color text_color: "black"

    property var impl_object: null
    implicitWidth: (impl_object) ? impl_object.implicitWidth : 24
    implicitHeight: (impl_object) ? impl_object.implicitHeight : 24

    gradient: Gradient {
        GradientStop { position: 0.0; color: "transparent" }
        GradientStop { position: 1.0; color: "transparent" }
    }

    Component.onCompleted: {
        root.init();
    }

    Connections {
        target: root
        function onDirectionChanged() {
            root.impl_object.destroy();
            root.init();
        }
    }

    function init() {
        var cmd = `
        import QtQuick 2.15
        import QtQuick.Controls.Material 2.15
        import QtQuick.Layouts 1.15
        `;
        var isHorizontal = direction === "left" || direction === "right";
        var alignmentCmd = `Layout.alignment: ${isHorizontal ? "Qt.AlignVCenter" : "Qt.AlignHCenter"}`;

        var iconCmd = "";
        if (icon_color == "#000000")
            icon_color = color;
        if (text_color == "#000000")
            text_color = color;

        if (root.icon !== "") {
            if (is_img) {
                iconCmd = `MImage {
                    source: root.icon
                    Layout.alignment: ${isHorizontal ? "Qt.AlignVCenter" : "Qt.AlignHCenter"}
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    fillMode: Image.PreserveAspectCrop
                    width: root.icon_size
                    height: root.icon_size
                }`;
            } else {
                iconCmd = `MIcon {
                    icon: root.icon
                    color: root.icon_color
                    ${alignmentCmd}
                    size: root.icon_size
                }`;
            }
        }
        var textCmd = `
        Text {
            text: root.text
            font.pixelSize: root.text_size
            font.family: root.font
            color: root.text_color
            ${alignmentCmd}
        }
        `;
        var componentCmd = direction === "left" || direction === "top" ? iconCmd + textCmd : textCmd + iconCmd;
        if (root.spacing == -1) {
            root.spacing = (root.icon_size + root.text_size) / 4.75;
        }
        cmd += `
        ${isHorizontal ? "RowLayout" : "ColumnLayout"} {
            spacing: ${isHorizontal ? "root.spacing" : "0"}
            ${componentCmd}
        }`;

        var object = Qt.createQmlObject(cmd, root, "dynamicComponent");
        root.impl_object = object;
    }
}