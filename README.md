# Todo List

This is a to-do list app that aims to help you manage your tasks. It uses the following technologies:

- Qt, PySide6
- Event driven programming
- QML, QtQuick
- YAML
- aiohttp, ayncio
- Thread, lock, and event queue

In addition to a simple to-do list, it has some unique features that I think
are worth sharing.

- It is a desktop app.
- It supports plugins. Currently, there is a plugin that checks grade changes
  on the student portal of my high school.
    - Becasue of the usage of multi-threading, the plugin does not block the GUI
      thread.
    - Because of async programming, multiple plugins can be run at the same
      time quickly.