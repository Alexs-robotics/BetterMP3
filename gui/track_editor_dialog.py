"""
track_editor_dialog.py
------------------------
Piccolo dialog modale per modificare il numero d'ordine (traccia) di
una canzone all'interno del suo album.
"""

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QSpinBox,
    QVBoxLayout,
)


class TrackEditorDialog(QDialog):
    def __init__(self, current_number: int, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit track number")

        self.spin_box = QSpinBox()
        self.spin_box.setRange(1, 999)
        self.spin_box.setValue(max(1, current_number))

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("New track number within the album:"))
        layout.addWidget(self.spin_box)
        layout.addWidget(buttons)

    def selected_number(self) -> int:
        return self.spin_box.value()
