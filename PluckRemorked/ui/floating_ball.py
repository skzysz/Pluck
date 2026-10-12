import ctypes
from PySide6.QtWidgets import (QWidget, QApplication, QGraphicsScene,
                               QGraphicsBlurEffect)
from PySide6.QtCore import Qt, Signal, QTimer, QPoint
from PySide6.QtGui import QPainter, QColor, QBrush, QPen, QPixmap, QPainterPath
import qtawesome as qta

from .theme import (BALL_SIZE, BG_BALL, BG_BALL_HOVER, BG_BALL_PRESSED,
                    ACCENT, BORDER_SUBTLE)


WDA_EXCLUDEFROMCAPTURE = 0x00000011


class FloatingBall(QWidget):
    clicked = Signal(object)

    def __init__(self, settings):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.settings = settings
        self.setFixedSize(BALL_SIZE, BALL_SIZE)
        self.setCursor(Qt.PointingHandCursor)
        self.setMouseTracking(True)

        x = settings.get("ball_x", 800)
        y = settings.get("ball_y", 400)
        self.move(x, y)

        self.old_pos = None
        self._hover = False
        self._pressed = False
        self._dragged = False
        self._press_pos = None

        self._bg_pixmap = None
        self._bg_padding = 0

        self._icon = qta.icon('fa5s.book', color=ACCENT).pixmap(22, 22)

        self._bg_timer = QTimer()
        self._bg_timer.timeout.connect(self._capture_background)
        self._bg_timer.setInterval(500)
        self._bg_timer.start()

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(80, self._exclude_from_capture)
        QTimer.singleShot(100, self._capture_background)

    def _exclude_from_capture(self):
        try:
            hwnd = int(self.winId())
            ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)
        except Exception:
            pass

    def _capture_background(self):
        if not self.isVisible():
            return
        try:
            rect = self.geometry()
            padding = 20
            screen = QApplication.primaryScreen()
            pixmap = screen.grabWindow(
                0,
                rect.x() - padding,
                rect.y() - padding,
                rect.width() + padding * 2,
                rect.height() + padding * 2
            )
            if pixmap.isNull():
                return

            blurred = pixmap
            for _ in range(2):
                scene = QGraphicsScene()
                item = scene.addPixmap(blurred)
                blur = QGraphicsBlurEffect()
                blur.setBlurRadius(40)
                item.setGraphicsEffect(blur)

                result = QPixmap(blurred.size())
                result.fill(Qt.transparent)
                painter = QPainter(result)
                scene.render(painter)
                painter.end()
                blurred = result

            self._bg_pixmap = blurred
            self._bg_padding = padding
            self.update()
        except Exception as e:
            print(f"Ball blur error: {e}")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        path = QPainterPath()
        path.addEllipse(0, 0, BALL_SIZE, BALL_SIZE)
        painter.setClipPath(path)

        if self._bg_pixmap is not None and not self._bg_pixmap.isNull():
            # Смещаем картинку так, чтобы её центр совпал с центром шара
            painter.drawPixmap(-self._bg_padding, -self._bg_padding, self._bg_pixmap)
            if self._pressed:
                painter.fillRect(self.rect(), QColor(5, 5, 12, 160))
            elif self._hover:
                painter.fillRect(self.rect(), QColor(20, 25, 45, 90))
            else:
                painter.fillRect(self.rect(), QColor(15, 18, 30, 120))
        else:
            if self._pressed:
                bg = QColor(BG_BALL_PRESSED)
            elif self._hover:
                bg = QColor(BG_BALL_HOVER)
            else:
                bg = QColor(BG_BALL)
            painter.fillRect(self.rect(), bg)

        painter.setClipping(False)

        if self._hover:
            painter.setPen(QPen(QColor(ACCENT), 1.5))
        else:
            painter.setPen(QPen(QColor(*BORDER_SUBTLE), 1))
        painter.drawEllipse(1, 1, BALL_SIZE - 2, BALL_SIZE - 2)

        icon_x = (BALL_SIZE - 22) // 2
        icon_y = (BALL_SIZE - 22) // 2
        painter.drawPixmap(icon_x, icon_y, self._icon)

    def enterEvent(self, event):
        self._hover = True
        self.update()

    def leaveEvent(self, event):
        self._hover = False
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._pressed = True
            self.old_pos = event.globalPosition().toPoint()
            self._press_pos = self.pos()
            self._dragged = False
            self.update()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.old_pos is not None:
            delta = event.globalPosition().toPoint() - self.old_pos
            if delta.manhattanLength() > 3:
                self._dragged = True
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPosition().toPoint()
            self.settings["ball_x"] = self.x()
            self.settings["ball_y"] = self.y()
            self._capture_background()

    def mouseReleaseEvent(self, event):
        was_pressed = self._pressed
        self._pressed = False
        self.update()
        if was_pressed and event.button() == Qt.LeftButton:
            if not self._dragged:
                self.clicked.emit(self.pos())
            self.old_pos = None
            self._dragged = False