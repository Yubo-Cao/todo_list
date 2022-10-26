import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Controls.Material 2.15
import QtQuick.Dialogs
import "components"

Item {
    id: root
    property var controller
    property var model

    ColumnLayout {
        anchors.margins: 16
        anchors.fill: parent

        RowLayout {
            Layout.fillWidth: true
            MIconLabel {
                icon: "note"
                text: "Note"
                icon_size: 32
                color: Material.accent
            }

            Item {
                Layout.fillWidth: true
            }

            RoundButton {
                Layout.alignment: Qt.AlignVCenter
                Material.background: Material.accent

                onClicked: {
                    controller.add()
                }

                contentItem: MIcon {
                    icon: "add"
                    color: "white"
                }
            }
        }

        GridView {
            id: noteView
            Layout.alignment: Qt.AlignTop
            Layout.fillWidth: true
            model: root.model
            cellWidth: 256 + 16
            cellHeight: 256 + 16

            delegate: RoundPane {
                Material.elevation: 1
                width: 256
                height: content.height + 24

                ColumnLayout {
                    id: content
                    width: parent.width

                    TextArea {
                        id: editor
                        text: model.text
                        wrapMode: Text.WordWrap
                        width: parent.width
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.alignment: Qt.AlignHCenter

                        Shortcut {
                            sequence: "Ctrl+Enter"
                            onActivated: {
                                focus = false
                            }
                        }

                        RowLayout {
                            id: controls
                            visible: false
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.rightMargin: 4

                            RoundButton {
                                anchors.top: parent.top - 16
                                Material.background: "transparent"

                                contentItem: MIcon {
                                    icon: "delete"
                                    size: 16
                                }
                                onClicked: {
                                    controller.delete(index)
                                }
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            propagateComposedEvents: true
                            z: -1
                            hoverEnabled: true
                            onEntered: {
                                controls.visible = true
                            }
                            onExited: {
                                model.text = editor.getText(0, editor.length)
                                controls.visible = false
                            }
                        }
                    }

                    MImage {
                        id: pictureItem
                        source: photo
                        height: 128
                        width: 232
                        Layout.alignment: Qt.AlignHCenter

                        MouseArea {
                            anchors.fill: parent
                            onClicked: {
                                pictureDialog.open()
                            }
                        }

                        FileDialog {
                            id: pictureDialog
                            title: "Select a picture"
                            currentFolder: "file:///" + Qt.resolvedUrl(".").toString()
                            nameFilters: ["Images (*.png *.jpg *.bmp)"]
                            visible: false
                            onAccepted: {
                                photo = selectedFile
                            }
                        }
                    }
                }
            }
        }

        // spacer
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
        }
    }
}