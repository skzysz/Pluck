import ctypes
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QLineEdit, QApplication, QGraphicsScene,
                               QGraphicsBlurEffect, QGraphicsOpacityEffect,
                               QScrollArea, QFrame)
from PySide6.QtCore import (Qt, Signal, QPropertyAnimation, QEasingCurve, QRect,
                            QSize, QTimer, QPoint, QParallelAnimationGroup)
from PySide6.QtGui import QColor, QPainter, QPen, QPainterPath, QPixmap
import qtawesome as qta

from .theme import (ACCENT, ACCENT_LIGHT, TEXT_WHITE, TEXT_GRAY, PANEL_WIDTH,
                    PANEL_HEIGHT, PANEL_RADIUS, HOVER, BALL_SIZE, BG_PANEL,
                    BORDER_SUBTLE, HARD_BG, HARD_BORDER, HARD_TEXT,
                    SOFT_BG, SOFT_BORDER, SOFT_TEXT)
from core.data import load_data


WDA_EXCLUDEFROMCAPTURE = 0x00000011


def is_hard_punishment(text):
    text_lower = text.lower()
    hard_keywords = ["ван", "бан", "навсегда", "перманент", "дней", "день",
                     "недел", "месяц", "год", "лет", "24 час", "час", "часов"]
    for kw in hard_keywords:
        if kw in text_lower:
            return True
    return False


class GlassPanel(QWidget):
    closed = Signal()
    builder_requested = Signal()

    def __init__(self, settings):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.settings = settings
        self.setFixedSize(PANEL_WIDTH, PANEL_HEIGHT)

        self._bg_pixmap = None
        self._drag_pos = None
        self._mode = "rules"

        self._build_ui()
        self._is_open = False

        self._bg_timer = QTimer()
        self._bg_timer.timeout.connect(self._capture_background)
        self._bg_timer.setInterval(500)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        header = QHBoxLayout()
        header.setSpacing(6)

        self.title = QLabel("Pluck ReMorked")
        self.title.setStyleSheet(
            f"color: {TEXT_WHITE}; font-size: 16px; font-weight: bold; "
            f"background: transparent; border: none;"
        )
        header.addWidget(self.title)
        header.addStretch()

        self.btn_builder = QPushButton()
        self.btn_builder.setCursor(Qt.PointingHandCursor)
        self.btn_builder.setIcon(qta.icon('fa5s.tools', color='#888'))
        self.btn_builder.setIconSize(QSize(12, 12))
        self.btn_builder.setFixedSize(28, 28)
        self.btn_builder.setToolTip("Билдер правил")
        self.btn_builder.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                border-radius: 14px;
            }}
            QPushButton:hover {{ background: {HOVER}; }}
        """)
        self.btn_builder.clicked.connect(self.builder_requested.emit)
        header.addWidget(self.btn_builder)

        self.btn_close = QPushButton()
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.setIcon(qta.icon('fa5s.times', color='#888'))
        self.btn_close.setIconSize(QSize(12, 12))
        self.btn_close.setFixedSize(28, 28)
        self.btn_close.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                border-radius: 14px;
            }}
            QPushButton:hover {{ background: {HOVER}; }}
        """)
        self.btn_close.clicked.connect(self.close_panel)
        header.addWidget(self.btn_close)

        layout.addLayout(header)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Поиск")
        self.search.setStyleSheet(f"""
            QLineEdit {{
                background: rgba(255, 255, 255, 25);
                border: 1px solid rgba(255, 255, 255, 45);
                border-radius: 10px;
                padding: 9px 14px;
                color: {TEXT_WHITE};
                font-size: 13px;
            }}
            QLineEdit:focus {{ border: 1px solid {ACCENT}; }}
        """)
        self.search.textChanged.connect(self._apply_search)
        layout.addWidget(self.search)

        toggle_row = QHBoxLayout()
        toggle_row.setSpacing(6)

        self.btn_rules = QPushButton("Правила")
        self.btn_rules.setCursor(Qt.PointingHandCursor)
        self.btn_rules.clicked.connect(lambda: self._set_mode("rules"))
        toggle_row.addWidget(self.btn_rules)

        self.btn_laws = QPushButton("Законы")
        self.btn_laws.setCursor(Qt.PointingHandCursor)
        self.btn_laws.clicked.connect(lambda: self._set_mode("laws"))
        toggle_row.addWidget(self.btn_laws)

        toggle_row.addStretch()
        layout.addLayout(toggle_row)

        self.list_scroll = QScrollArea()
        self.list_scroll.setWidgetResizable(True)
        self.list_scroll.setStyleSheet(f"""
            QScrollArea {{ border: none; background: transparent; }}
            QScrollBar:vertical {{ background: transparent; width: 6px; }}
            QScrollBar::handle:vertical {{ background: #333; border-radius: 3px; min-height: 20px; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
        """)

        self.list_content = QWidget()
        self.list_content.setStyleSheet("background: transparent;")
        self.list_layout = QVBoxLayout(self.list_content)
        self.list_layout.setContentsMargins(0, 0, 6, 0)
        self.list_layout.setSpacing(6)
        self.list_layout.addStretch()

        self.list_scroll.setWidget(self.list_content)
        layout.addWidget(self.list_scroll, stretch=1)

        self.footer = QLabel("Pluck ReMorked beta")
        self.footer.setAlignment(Qt.AlignCenter)
        self.footer.setStyleSheet(
            f"color: {TEXT_GRAY}; font-size: 10px; "
            f"background: transparent; border: none;"
        )
        layout.addWidget(self.footer)

        self._update_mode_buttons()
        self._load_data()

    def _update_mode_buttons(self):
        active = f"""
            QPushButton {{
                background: {ACCENT};
                color: {TEXT_WHITE};
                border: none;
                border-radius: 8px;
                padding: 6px 16px;
                font-size: 12px;
                font-weight: bold;
            }}
        """
        inactive = f"""
            QPushButton {{
                background: rgba(255, 255, 255, 12);
                color: {TEXT_GRAY};
                border: 1px solid rgba(255, 255, 255, 25);
                border-radius: 8px;
                padding: 6px 16px;
                font-size: 12px;
            }}
            QPushButton:hover {{ background: rgba(255, 255, 255, 25); }}
        """
        if self._mode == "rules":
            self.btn_rules.setStyleSheet(active)
            self.btn_laws.setStyleSheet(inactive)
        else:
            self.btn_rules.setStyleSheet(inactive)
            self.btn_laws.setStyleSheet(active)

    def _set_mode(self, mode):
        self._mode = mode
        self._update_mode_buttons()
        self._refresh_list(self.search.text())

    def _load_data(self):
        custom = self.settings.get("custom_data_path", "")
        self._data = load_data(force_refresh=True, custom_path=custom)

    def _refresh_list(self, query=""):
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        items = self._data.get(self._mode, [])
        if query:
            q = query.lower()
            items = [i for i in items if q in i.get("title", "").lower()
                     or q in i.get("summary", "").lower()
                     or q in i.get("id", "").lower()
                     or q in i.get("description", "").lower()]

        if not items:
            lbl = QLabel("Пусто. Открой билдер.")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(f"color: {TEXT_GRAY}; font-size: 12px; padding: 30px; background: transparent;")
            self.list_layout.addWidget(lbl)
            self.list_layout.addStretch()
            return

        for item_data in items:
            card = self._make_card(item_data)
            self.list_layout.addWidget(card)

        self.list_layout.addStretch()

    def _make_card(self, item):
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background: rgba(25, 25, 35, 200);
                border: 1px solid rgba(255, 255, 255, 25);
                border-radius: 8px;
            }}
            QFrame:hover {{
                background: rgba(40, 40, 55, 220);
                border: 1px solid {ACCENT};
            }}
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(3)

        row = QHBoxLayout()
        row.setSpacing(6)

        id_lbl = QLabel(item.get("id", ""))
        id_lbl.setStyleSheet(f"color: {ACCENT}; font-size: 12px; font-weight: bold; background: transparent; border: none;")
        row.addWidget(id_lbl)

        title = QLabel(item.get("title", ""))
        title.setWordWrap(True)
        title.setStyleSheet(f"color: {TEXT_WHITE}; font-size: 12px; background: transparent; border: none;")
        row.addWidget(title, stretch=1)
        layout.addLayout(row)

        summary = QLabel(item.get("summary", ""))
        summary.setWordWrap(True)
        summary.setStyleSheet(f"color: {TEXT_GRAY}; font-size: 10px; background: transparent; border: none;")
        layout.addWidget(summary)

        if item.get("punishment"):
            first = item["punishment"][0]
            text = first if len(first) <= 30 else first[:28] + "..."
            if is_hard_punishment(first):
                style = f"color: {HARD_TEXT}; background-color: {HARD_BG}; border: 1px solid {HARD_BORDER};"
            else:
                style = f"color: {SOFT_TEXT}; background-color: {SOFT_BG}; border: 1px solid {SOFT_BORDER};"
            tag = QLabel(text)
            tag.setStyleSheet(f"{style} border-radius: 4px; padding: 2px 8px; font-size: 10px;")
            tag_row = QHBoxLayout()
            tag_row.setSpacing(4)
            tag_row.addWidget(tag)
            if len(item["punishment"]) > 1:
                extra = QLabel(f"+{len(item['punishment']) - 1}")
                extra.setStyleSheet(f"color: {TEXT_GRAY}; font-size: 10px; background: transparent; border: none;")
                tag_row.addWidget(extra)
            tag_row.addStretch()
            layout.addLayout(tag_row)

        return card

    def _apply_search(self, text):
        self._refresh_list(text)

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
            screen = QApplication.primaryScreen()
            pixmap = screen.grabWindow(0, rect.x(), rect.y(), rect.width(), rect.height())
            if pixmap.isNull():
                return

            scene = QGraphicsScene()
            item = scene.addPixmap(pixmap)
            blur = QGraphicsBlurEffect()
            blur.setBlurRadius(30)
            item.setGraphicsEffect(blur)

            result = QPixmap(pixmap.size())
            result.fill(Qt.transparent)
            painter = QPainter(result)
            scene.render(painter)
            painter.end()

            self._bg_pixmap = result
            self.update()
        except Exception as e:
            print(f"Blur error: {e}")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), PANEL_RADIUS, PANEL_RADIUS)
        painter.setClipPath(path)

        if self._bg_pixmap is not None and not self._bg_pixmap.isNull():
            painter.drawPixmap(0, 0, self._bg_pixmap)
            painter.fillRect(self.rect(), QColor(10, 10, 18, 175))
        else:
            painter.fillRect(self.rect(), QColor(*BG_PANEL))

        painter.setClipping(False)
        painter.setPen(QPen(QColor(*BORDER_SUBTLE), 1))
        painter.drawRoundedRect(0, 0, self.width() - 1, self.height() - 1,
                                PANEL_RADIUS, PANEL_RADIUS)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            child = self.childAt(event.position().toPoint())
            if child is None or child is self:
                self._drag_pos = event.globalPosition().toPoint()
                event.accept()
            else:
                super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self._drag_pos is not None:
            delta = event.globalPosition().toPoint() - self._drag_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self._drag_pos = event.globalPosition().toPoint()
            self._capture_background()
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def open_from(self, ball_pos):
        end_x = ball_pos.x() - PANEL_WIDTH // 2 + BALL_SIZE // 2
        end_y = ball_pos.y() + BALL_SIZE + 10

        screen = QApplication.primaryScreen().geometry()
        end_x = max(20, min(end_x, screen.width() - PANEL_WIDTH - 20))
        end_y = max(20, min(end_y, screen.height() - PANEL_HEIGHT - 20))

        end_rect = QRect(end_x, end_y, PANEL_WIDTH, PANEL_HEIGHT)

        self.setGeometry(end_rect)
        self.setWindowOpacity(0.0)
        self.show()
        self.raise_()

        QTimer.singleShot(80, self._exclude_from_capture)
        QTimer.singleShot(100, self._capture_background)

        self._bg_timer.start()

        self._fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self._fade_anim.setDuration(280)
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._fade_anim.start()

        self._is_open = True

    def close_panel(self):
        if not self._is_open:
            return
        self._bg_timer.stop()

        self._fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self._fade_anim.setDuration(240)
        self._fade_anim.setStartValue(1.0)
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.setEasingCurve(QEasingCurve.InCubic)
        self._fade_anim.finished.connect(self._on_closed)
        self._fade_anim.start()

    def _on_closed(self):
        self.hide()
        self._is_open = False
        self._bg_pixmap = None
        self.closed.emit()