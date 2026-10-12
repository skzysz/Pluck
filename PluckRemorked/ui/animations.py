from PySide6.QtCore import QPropertyAnimation, QEasingCurve
from PySide6.QtWidgets import QGraphicsOpacityEffect


def fade_in(widget, duration=250, start=0.0, end=1.0, on_done=None):
    effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effect)
    anim = QPropertyAnimation(effect, b"opacity")
    anim.setDuration(duration)
    anim.setStartValue(start)
    anim.setEndValue(end)
    anim.setEasingCurve(QEasingCurve.OutCubic)
    if on_done:
        anim.finished.connect(on_done)
    anim.start()
    widget._fade_anim = anim
    return anim


def animate_geometry(widget, duration=350, start=None, end=None,
                     easing=QEasingCurve.OutCubic, on_done=None):
    anim = QPropertyAnimation(widget, b"geometry")
    anim.setDuration(duration)
    anim.setStartValue(start if start is not None else widget.geometry())
    anim.setEndValue(end if end is not None else widget.geometry())
    anim.setEasingCurve(easing)
    if on_done:
        anim.finished.connect(on_done)
    anim.start()
    widget._geo_anim = anim
    return anim