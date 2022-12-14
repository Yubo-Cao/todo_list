import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Controls.Material 2.15
import QtQuick.Dialogs
import "components"

ListView {
    id: root

    delegate: RoundPane {
        Material.elevation: 1
        width: parent.width

        RowLayout {
            spacing: 8
            width: parent.width

            RowLayout {
                id: content
                width: parent.width

                CheckBox {
                    id: checkBox
                    checked: completed
                    onClicked: {
                        completed = !completed
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
                            text: title
                            font.pointSize: 14
                            MouseArea {
                                anchors.fill: parent
                                onClicked: {
                                    titleText.visible = false
                                    titleEditor.visible = true
                                    titleEditor.forceActiveFocus()
                                }
                            }
                        }
                        // editor for title
                        TextField {
                            id: titleEditor
                            width: titleText.width
                            height: titleText.height

                            text: title
                            font.pointSize: 14
                            visible: false
                            onEditingFinished: {
                                title = text
                                titleText.visible = true
                                titleEditor.visible = false
                            }
                        }

                        Text {
                            id: descriptionText
                            font.pointSize: 10
                            text: description.length > 0 ? description : "Description"
                            MouseArea {
                                anchors.fill: parent
                                onClicked: {
                                    descriptionText.visible = false
                                    descriptionEditor.visible = true
                                }
                            }
                        }

                        // editor for description (textarea)
                        TextArea {
                            id: descriptionEditor
                            font.pointSize: 10

                            text: description
                            width: descriptionText.width
                            height: descriptionText.height
                            placeholderText: "Description"
                            visible: false

                            onEditingFinished: {
                                 description = text
                                 descriptionEditorView.visible = false
                                 descriptionText.visible = true
                            }

                            KeyNavigation.tab: dueDateEditor

                            Shortcut {
                                sequence: "Ctrl+Return"
                                onActivated: {
                                    description = descriptionEditor.getText(0, descriptionEditor.length)
                                    descriptionEditor.visible = false
                                    descriptionText.visible = true
                                }
                            }
                        }
                    }

                    RowLayout {
                        id: dateRow
                        spacing: 16

                        MIconLabel {
                            id: dueDateIconLabel
                            icon: "schedule"
                            color: Material.color(Material.Grey, Material.Shade500)
                            text: "Due " + get_date_string(due_date)
                            icon_size: 12
                            text_size: 10

                            MouseArea {
                                anchors.fill: parent
                                onClicked: {
                                    dueDateEditor.visible = true
                                    dueDateEditor.forceActiveFocus()
                                }
                            }
                        }
                        // editor for due date
                        Popup {
                            id: dueDateEditor
                            x: (parent.width - width) / 2
                            y: (parent.height - height) / 2

                            visible: false
                            closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
                            focus: true
                            parent: Overlay.overlay

                            RoundPane {
                                MDatePicker {
                                    id: dueDatePicker
                                    anchors.fill: parent
                                    on_ok: function () {
                                        dueDateEditor.visible = false
                                        due_date = dueDatePicker.selectedDate
                                    }
                                    on_cancel: function () {
                                        dueDateEditor.visible = false
                                    }
                                }
                            }
                        }

                        MIconLabel {
                            id: createdDateIconLabel
                            icon: "schedule"
                            color: Material.color(Material.Grey, Material.Shade500)
                            text: "Created " + get_date_string(created_date)
                            icon_size: 12
                            text_size: 10

                            MouseArea {
                                anchors.fill: parent
                                onClicked: {
                                    createdDateEditor.visible = true
                                    createdDateEditor.forceActiveFocus()
                                }
                            }
                        }
                        // editor for created date
                        Popup {
                            id: createdDateEditor
                            x: (parent.width - width) / 2
                            y: (parent.height - height) / 2

                            visible: false
                            closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
                            focus: true
                            parent: Overlay.overlay

                            RoundPane {
                                MDatePicker {
                                    id: createdDatePicker
                                    anchors.fill: parent
                                    on_ok: function () {
                                        createdDateEditor.visible = false
                                        created_date = createdDatePicker.selectedDate
                                    }
                                    on_cancel: function () {
                                        createdDateEditor.visible = false
                                    }
                                }
                            }
                        }
                    }
                }

                // Spacer
                Item {
                    Layout.fillWidth: true
                }

                MImage {
                    id: pictureItem
                    source: photo
                    height: 64
                    width: 64

                    MouseArea {
                        anchors.fill: parent
                        onClicked: {
                            pictureDialog.open()
                        }
                    }
                }

                // editor for picture
                // Filedialog
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

    function get_date_string(date) {
        if (date === null || date === undefined) {
            return "unknown";
        } else {
            return date.toLocaleDateString(Locale.systemLocale, Locale.ShortFormat);
        }
    }

    function is_empty(data) {
        return data === null || data === undefined || data == "" || data == "null";
    }
}