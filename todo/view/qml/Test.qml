import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Controls.Material 2.15

ApplicationWindow {
    id: window
    visible: true
    width: 640
    height: 480
    title: "Todo List"

    property string page_title: "My todos"

    Material.primary: Material.Blue
    Material.accent: Material.Blue

    FontLoader { source: "../fonts/MaterialIcons-Regular.ttf" }

    header: ToolBar {
        RowLayout {
            spacing: 16
            anchors.fill: parent

            IconButton {
                Layout.alignment: Qt.AlignVCenter
                Layout.leftMargin: 16
                Layout.bottomMargin: -2

                icon: "menu"
                onClicked: function() {
                    drawer.open()
                }
            }

            Label {
                id: titleLabel
                text: page_title
                font.pixelSize: 20
                verticalAlignment: Qt.AlignVCenter
                horizontalAlignment: Qt.AlignLeft
                Layout.fillWidth: true
            }

            IconButton {
                Layout.alignment: Qt.AlignVCenter
                Layout.rightMargin: 16
                icon: "more_vert"

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

            delegate: ItemDelegate {
                width: parent.width
                text: model.title
                contentItem: RowLayout {
                    spacing: 16
                    anchors.fill: parent
                    Text {
                        text: model.icon
                        font.pixelSize: 24
                        Layout.leftMargin: 16
                        verticalAlignment: Qt.AlignVCenter
                        horizontalAlignment: Qt.AlignLeft
                        font.family: "Material Icons"
                    }

                    Label {
                        text: model.title
                        font.pixelSize: 16
                        verticalAlignment: Qt.AlignVCenter
                        horizontalAlignment: Qt.AlignLeft
                        Layout.fillWidth: true
                    }
                }
                highlighted: ListView.isCurrentItem
                onClicked: {
                    if (listView.currentIndex != index) {
                        listView.currentIndex = index
                        titleLabel.text = model.title
                        stackView.replace(model.source)
                    }
                    drawer.close()
                }
            }

            model: ListModel {
                ListElement { title: "My todos"; source: "TodoView.qml"; icon: "list" }
                ListElement { title: "My notes"; source: "Notes.qml"; icon: "note" }
                ListElement { title: "My grade"; source : "Grade.qml"; icon: "grade" }
                ListElement { title: "Abount"; source: "About.qml"; icon: "info" }
                ListElement { title: "Settings"; source: "Settings.qml"; icon: "settings" }
                ListElement { title: "Exit"; source: "Exit.qml"; icon: "exit_to_app" }
            }
            ScrollIndicator.vertical: ScrollIndicator { }
        }
    }

    StackView {
        id: stackView
        anchors.fill: parent
    }

    Component.onCompleted: {
        stackView.push("TodoView.qml")
    }
}




