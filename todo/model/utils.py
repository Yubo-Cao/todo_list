from datetime import datetime
from hashlib import md5
from pathlib import Path
from typing import Any

import PIL.Image as Image
from PySide6.QtCore import QDateTime, QUrl
from PySide6.QtGui import QPixmap, QImage

from todo.globals import data_path


def to_qt_data(data: Any) -> Any:
    """
    Convert data to a Qt compatible data type.
    """
    if data is None:
        return None
    if isinstance(data, datetime):
        return QDateTime(data.year, data.month, data.day, data.hour, data.minute, data.second)
    if isinstance(data, Image.Image):
        buf = data.tobytes()
        return QPixmap(QImage.fromData(buf, QImage.Format_RGB888))
    if isinstance(data, Path):
        return QUrl.fromLocalFile(str(data))
    return data


def save_image(path: str | Path) -> Path:
    """
    Save an image to the data directory.
    """

    path = Path(path)

    if path.parent.parent == data_path:
        print("Image already in data directory")
        return path
    dst = data_path / "Images" / md5(path.read_bytes()).hexdigest()
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst = dst.with_suffix('.png')
    if not dst.exists():
        with Image.open(path) as img:
            img.save(dst)
    return dst


def provide_qt_data(fn):
    """
    Decorator to convert data from Qt compatible data types.
    """

    def wrapper(*args, **kwargs):
        return to_qt_data(fn(*args, **kwargs))

    return wrapper


def from_qt_data(data: Any) -> Any:
    """
    Convert data from a Qt compatible data type.
    """
    if data is None:
        return None
    if isinstance(data, QDateTime):
        return datetime(data.date().year(), data.date().month(), data.date().day(), data.time().hour(),
                        data.time().minute(), data.time().second())
    if isinstance(data, QUrl):
        return Path(data.toLocalFile())
    if isinstance(data, QPixmap):
        buf = data.toImage().convertToFormat(QImage.Format_RGB888).toBytes()
        return Image.frombytes("RGB", (data.width(), data.height()), buf)
    return data


def provide_python_data(fn):
    """
    Decorator to convert data to Qt compatible data types.
    """

    def wrapper(*args, **kwargs):
        return from_qt_data(fn(*args, **kwargs))

    return wrapper


def require_python_data(fn):
    """
    Decorator to convert arguments from Qt compatible data types.
    """

    def wrapper(*args, **kwargs):
        return fn(*[from_qt_data(arg) for arg in args], **{k: from_qt_data(v) for k, v in kwargs.items()})

    return wrapper
