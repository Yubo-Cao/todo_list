import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Controls.Material 2.15
import "components"

Item {
    id: root
    property alias model: listView.model

    ColumnLayout {
        anchors {
            fill: parent
            margins: 16
        }

        // header


        RowLayout {
            Layout.fillWidth: true
            MIconLabel {
                icon: "task"
                text: "Task"
                icon_size: 32
                color: Material.accent
            }
            Item {
                Layout.fillWidth: true
            }
            ComboBox {
                id: combo
                model: ["All", "Active", "Completed"]
                currentIndex: 0
            }
        }

        // task list
        TodoListView {
            y: 200
            id: listView
            Layout.fillWidth: true
            Layout.fillHeight: true
        }
    }
}