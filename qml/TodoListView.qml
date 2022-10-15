import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

ListView {
    Layout.fillWidth: true
    Layout.fillHeight: true
    model: model
    spacing: 8

    delegate: ItemDelegate {
        text: modelData
    }
}
