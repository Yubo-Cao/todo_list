import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "components"

RoundPane {
    padding: 8
    radius: 8
    Material.elevation: elevation
    font.family: "Roboto"
    Layout.fillWidth: true
    Layout.preferredHeight: 100
    Layout.minimumHeight: 75
    width: parent.width

    
    RowLayout {
        id: content
        spacing: 8

        MouseArea {
            id: mouseArea
            width: parent.width
            height: parent.height
            propagateComposedEvents: true

            hoverEnabled: true
            onEntered: {
                elevation = 2
                cursorShape = Qt.PointingHandCursor
            }
            onExited: {
                elevation = 1
            }
        }

        CheckBox {
            id: checkBox
            checked: completed
            onCheckedChanged: {
                completed = checked
            }
            Layout.fillWidth: false
        }

        ColumnLayout {
            id: contentItem
            spacing: 8
            Layout.alignment: Qt.AlignVCenter

            ColumnLayout {
                id: titleItem
                spacing: 2
                Text {
                    id: titleText
                    text: title.length > 40 ? title.substring(0, 40) + "..." : title
                    font.pointSize: 14
                }
                Text {
                    id: descriptionText
                    text: description.length > 50 ? description.substring(0, 50) + "..." : description
                    font.pointSize: 10
                    visible: description !== ""
                }
            }

            RowLayout {
                id: dateRow
                spacing: 4
                visible: display_date
                
                RowLayout {
                    spacing: 2

                    Text {
                        text: "\ue855"
                        font.family: "Material Icons"
                        font.pixelSize: 16
                        color: Material.color(Material.Grey, Material.Shade500)
                    }
                    Text {
                        id: dueDateText
                        text: "Due: " + due_date.toLocaleDateString(Locale.systemLocale, Locale.ShortFormat)
                        font.pointSize: 8
                        color: Material.color(Material.Grey, Material.Shade500)
                        Layout.alignment: Qt.AlignVCenter
                    }
                }


                RowLayout {
                    spacing: 2

                    Text {
                        text: "\ue8b5"
                        font.family: "Material Icons"
                        font.pixelSize: 16
                        color: Material.color(Material.Grey, Material.Shade500)
                    }
                    Text {
                        id: createDateText
                        text: "Started: " + create_date.toLocaleDateString(Locale.systemLocale, Locale.ShortFormat)
                        font.pointSize: 8
                        color: Material.color(Material.Grey, Material.Shade500)
                        Layout.alignment: Qt.AlignVCenter
                    }
                }
            }
        }

        Image {
            id: pictureItem
            source: photo
            Layout.alignment: Qt.AlignVCenter
            Layout.preferredWidth: 30
            Layout.preferredHeight: 30
            visible: photo !== null && photo !== "null" && photo !== ""
        }
    }
}