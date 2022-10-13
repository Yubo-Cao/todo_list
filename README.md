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

Todo List is a free software that helps you to keep track
of your tasks. It is written in Python and uses Qt for the GUI. As 
a result, it provides a tight integration with the desktop environment,
as compared to web apps. Asynchronous programming is used to make the integrations of the plugins
run in the background in efficient way. Currently, an integration of 
student portal of my high school is provided, which checks the grade
changes and notifies the user. API is provided for developers
to write their own plugins. Because the usage of abstract class/interface,
type-hinting, and extensive doc strings, it is easy to write plugins
without knowing the implementation details of the app.