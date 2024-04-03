import pathlib

from PyQt5 import QtCore, QtWidgets


def get_directory(
        parent: QtWidgets.QWidget,
        identifier: str,
        caption: str = "Select directory",
        force_dialog: bool = False,
        ):
    """Retrieve the path for a given identifier

    When called for the first time, a directory dialog is opened and
    the user can select the target directory. The directory is then stored
    in the settings.
    When called for the second time, a dialog will only pop up when
    `show_dialog` is set to `True`, otherwise the value from the settings
    is returned.
    """
    path = "."  # default value
    settings = QtCore.QSettings()
    dir_settings = settings.value(f"paths/{identifier}", path)
    if dir_settings and pathlib.Path(dir_settings).exists():
        path = dir_settings
    else:
        force_dialog = True

    if force_dialog:
        dir_user = QtWidgets.QFileDialog.getExistingDirectory(
            parent=parent,
            caption=caption,
            directory=settings.value(f"paths/{identifier}", path)
        )
        if dir_user:
            path = dir_user
            settings.setValue(f"paths/{identifier}", path)

    return path
