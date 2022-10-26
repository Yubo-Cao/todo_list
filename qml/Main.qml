import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Controls.Material 2.15
import "components"

ApplicationWindow {
    id: window
    visible: true
    width: 1024
    height: 768
    title: "Todo List"

    property string page_title: "My todos"

    Material.primary: Material.Blue
    Material.accent: Material.Blue

    FontLoader {
        source: "../fonts/MaterialIcons-Regular.ttf"
    }
    FontLoader {
        source: "../fonts/Roboto-Regular.ttf"
    }
    FontLoader {
        source: "../fonts/Roboto-Thin.ttf"
    }

    header: ToolBar {
        RowLayout {
            spacing: 8
            anchors.leftMargin: 8
            anchors.rightMargin: 8
            anchors.fill: parent

            RoundButton {
                Layout.alignment: Qt.AlignVCenter
                Material.background: "transparent"

                onClicked: function() {
                    drawer.open()
                }

                contentItem: MIcon {
                    icon: "menu"
                    color: "white"
                }
            }

            Text {
                id: titleLabel
                text: page_title
                font.pixelSize: 20
                color: "white"
                verticalAlignment: Text.AlignVCenter
                Layout.alignment: Qt.AlignVCenter
                Layout.fillWidth: true
            }

            RoundButton {
                Layout.alignment: Qt.AlignVCenter
                // flat
                Material.background: "transparent"

                contentItem: MIcon {
                    icon: "more_vert"
                    color: "white"
                }

                onClicked: function() {
                    optionsMenu.open()
                }

                Menu {
                    id: optionsMenu
                    x: parent.width - width
                    transformOrigin: Menu.TopRight

                    MenuItem {
                        text: "Settings"
                        onTriggered: settingsPopup.open()
                    }
                    MenuItem {
                        text: "About"
                        onTriggered: aboutDialog.open()
                    }
                }
            }
        }
    }



    Drawer {
        id: drawer
        width: 256
        height: window.height

        ListView {
            id: listView
            currentIndex: -1
            anchors.fill: parent
            model: navigationModel

            delegate: ItemDelegate {
                width: parent.width
                text: title
                contentItem: MIconLabel {
                    icon: model.icon
                    text: model.title
                    text_size: 16
                }
                highlighted: ListView.isCurrentItem
                onClicked: {
                    if (listView.currentIndex != index) {
                        listView.currentIndex = index
                        titleLabel.text = title
                        stackView.replace(source, {
                            "model": item_model,
                            "controller": item_controller
                        })
                    }
                    drawer.close()
                }
            }

            ScrollIndicator.vertical: ScrollIndicator {}
        }
    }

    StackView {
        id: stackView
        anchors.fill: parent
    }
}