import QtQuick 2.15
import QtQuick.Controls.Material 2.15
import QtQuick.Layouts 1.15

Item {
    id: root

    property int spacing: 8
    property string direction: "left"

    property string icon: ""
    property string text: ""
    property string font: "Roboto"
    property color color: "black"

    Component.onCompleted: {
        var cmd = `
        import QtQuick 2.15
        import QtQuick.Controls.Material 2.15
        import QtQuick.Layouts 1.15
        `;
        var isHorizontal = direction === "left" || direction === "right";
        var alignmentCmd = `Layout.alignment: ${isHorizontal ? "Qt.AlignVCenter" : "Qt.AlignHCenter"}`;
        var iconCmd = `
        MIcon {
            icon: root.icon
            color: root.color
            ${alignmentCmd}
        }
        `;
        var textCmd = `
        Text {
            text: root.text
            font: root.font
            color: root.color
            ${alignmentCmd}
        }
        `;
        var componentCmd = direction === "left" || direction === "top" ? iconCmd + textCmd : textCmd + iconCmd;
        cmd += `
        ${isHorizontal ? "RowLayout" : "ColumnLayout"} {
            spacing: ${isHorizontal ? "root.spacing" : "0"}
            ${componentCmd}
        }`;

        console.log(cmd);
        Qt.createQmlObject(cmd, root, "dynamicComponent");
    }
}