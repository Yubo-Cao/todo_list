import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Controls.Material 2.15
import QtQuick.Controls.Material.impl 2.15

Pane {
    id: control
    property int radius: 2

    background: Rectangle {
        color: control.Material.background
        radius: control.Material.elevation > 0 ? control.radius : 0

        layer.enabled: control.enabled && control.Material.elevation > 0
        layer.effect: ElevationEffect {
            elevation: control.Material.elevation
        }
    }
}