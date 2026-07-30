"""
player_controls.py
-------------------
Widget Qt con i controlli di riproduzione: play/pausa, precedente/
successivo, selezione della velocità (1x, 1.5x, 2x), barra di
avanzamento trascinabile per saltare a un punto preciso del brano, e
controllo del volume.

Il widget è "dumb": riceve un PlaybackEngine da pilotare e notifica il
main_window quando l'utente interagisce, ma non contiene logica di
business.
"""

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from core.player import PlaybackEngine


def _format_time(seconds: float) -> str:
    seconds = max(0, int(seconds))
    minutes, secs = divmod(seconds, 60)
    return f"{minutes:02d}:{secs:02d}"


class PlayerControls(QWidget):
    play_pause_clicked = Signal()
    next_clicked = Signal()
    previous_clicked = Signal()

    def __init__(self, engine: PlaybackEngine, parent=None) -> None:
        super().__init__(parent)
        self.engine = engine
        self._seeking = False

        self.now_playing_label = QLabel("Nessun brano in riproduzione")
        self.now_playing_label.setStyleSheet("font-weight: 600; font-size: 14px;")

        # --- Barra di avanzamento con tempo trascorso/totale ---
        self.elapsed_label = QLabel("00:00")
        self.total_label = QLabel("00:00")
        self.seek_slider = QSlider(Qt.Horizontal)
        self.seek_slider.setRange(0, 1000)
        self.seek_slider.sliderPressed.connect(self._on_seek_start)
        self.seek_slider.sliderReleased.connect(self._on_seek_end)

        seek_row = QHBoxLayout()
        seek_row.addWidget(self.elapsed_label)
        seek_row.addWidget(self.seek_slider)
        seek_row.addWidget(self.total_label)

        # --- Pulsanti di trasporto ---
        self.prev_button = QPushButton("⏮")
        self.play_pause_button = QPushButton("▶")
        self.next_button = QPushButton("⏭")
        for b in (self.prev_button, self.play_pause_button, self.next_button):
            b.setFixedWidth(48)

        self.prev_button.clicked.connect(self._on_previous)
        self.play_pause_button.clicked.connect(self._on_play_pause)
        self.next_button.clicked.connect(self._on_next)

        # --- Velocità di riproduzione ---
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["0.75x", "1x", "1.25x", "1.5x", "2x"])
        self.speed_combo.setCurrentText("1x")
        self.speed_combo.currentTextChanged.connect(self._on_speed_changed)

        # --- Volume ---
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(80)
        self.volume_slider.setFixedWidth(120)
        self.volume_slider.valueChanged.connect(self.engine.set_volume)
        self.engine.set_volume(80)

        transport_row = QHBoxLayout()
        transport_row.addWidget(self.prev_button)
        transport_row.addWidget(self.play_pause_button)
        transport_row.addWidget(self.next_button)
        transport_row.addStretch()
        transport_row.addWidget(QLabel("Velocità:"))
        transport_row.addWidget(self.speed_combo)
        transport_row.addSpacing(20)
        transport_row.addWidget(QLabel("Volume:"))
        transport_row.addWidget(self.volume_slider)

        layout = QVBoxLayout(self)
        layout.addWidget(self.now_playing_label)
        layout.addLayout(seek_row)
        layout.addLayout(transport_row)

        # Timer che aggiorna la barra di avanzamento ogni 500ms mentre si suona.
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(500)
        self._refresh_timer.timeout.connect(self._refresh_progress)
        self._refresh_timer.start()

    # -- Slot interni -------------------------------------------------
    def _on_play_pause(self) -> None:
        self.play_pause_clicked.emit()

    def _on_next(self) -> None:
        self.next_clicked.emit()

    def _on_previous(self) -> None:
        self.previous_clicked.emit()

    def _on_speed_changed(self, text: str) -> None:
        rate = float(text.replace("x", ""))
        self.engine.set_speed(rate)

    def _on_seek_start(self) -> None:
        self._seeking = True

    def _on_seek_end(self) -> None:
        fraction = self.seek_slider.value() / 1000.0
        self.engine.seek_to_fraction(fraction)
        self._seeking = False

    def _refresh_progress(self) -> None:
        if self._seeking:
            return
        duration = self.engine.get_duration_seconds()
        position = self.engine.get_position_seconds()
        if duration > 0:
            self.seek_slider.setValue(int((position / duration) * 1000))
        self.elapsed_label.setText(_format_time(position))
        self.total_label.setText(_format_time(duration))
        self.play_pause_button.setText("⏸" if self.engine.is_playing() else "▶")

    def set_now_playing_text(self, text: str) -> None:
        self.now_playing_label.setText(text)
