import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

ApplicationWindow {
    visible: true
    width: 640
    height: 480
    title: qsTr("Hello World")

    Material.accent: Material.Blue
    
    TodoList {
        id: todoList
        anchors.fill: parent
    }

    FontLoader { source: "fonts/MaterialIcons-Regular.ttf" }
}



