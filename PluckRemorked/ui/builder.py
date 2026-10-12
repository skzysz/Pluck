import ctypes
import json
import subprocess
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QLineEdit, QTextEdit, QListWidget,
                               QListWidgetItem, QApplication,
                               QGraphicsScene, QGraphicsBlurEffect)
from PySide6.QtCore import Qt, Signal, QSize, QTimer
from PySide6.QtGui import QColor, QPainter, QPen, QPainterPath, QPixmap
import qtawesome as qta

from .theme import (ACCENT, ACCENT_LIGHT, TEXT_WHITE, TEXT_GRAY,
                    BORDER_SUBTLE, HOVER, PANEL_RADIUS, BG_PANEL)


WDA_EXCLUDEFROMCAPTURE = 0x00000011
BUILDER_WIDTH = 1000
BUILDER_HEIGHT = 700


class RuleBuilder(QWidget):
    saved = Signal(str)

    def __init__(self, settings):
        super().__init__(None, Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.settings = settings
        self.setFixedSize(BUILDER_WIDTH, BUILDER_HEIGHT)

        self._data = {"rules": [], "laws": []}
        self._mode = "rules"
        self._current_index = -1
        self._drag_pos = None
        self._bg_pixmap = None

        self._build_ui()

        self._bg_timer = QTimer()
        self._bg_timer.timeout.connect(self._capture_background)
        self._bg_timer.setInterval(500)

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(80, self._exclude_from_capture)
        QTimer.singleShot(100, self._capture_background)
        self._bg_timer.start()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        header = QHBoxLayout()
        header.setSpacing(8)

        title = QLabel("Билдер правил и законов")
        title.setStyleSheet(
            f"color: {TEXT_WHITE}; font-size: 18px; font-weight: bold; "
            f"background: transparent; border: none;"
        )
        header.addWidget(title)
        header.addStretch()

        self.btn_new = QPushButton("  Новый профиль")
        self.btn_new.setCursor(Qt.PointingHandCursor)
        self.btn_new.setIcon(qta.icon('fa5s.file', color=ACCENT_LIGHT))
        self.btn_new.setIconSize(QSize(13, 13))
        self.btn_new.setFixedHeight(32)
        self.btn_new.setStyleSheet(f"""
            QPushButton {{
                background: rgba(51, 95, 255, 40);
                color: {TEXT_WHITE};
                border: 1px solid {ACCENT};
                border-radius: 8px;
                padding: 0 14px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background: rgba(51, 95, 255, 80); }}
        """)
        self.btn_new.clicked.connect(self._new_profile)
        header.addWidget(self.btn_new)

        btn_close = QPushButton()
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.setIcon(qta.icon('fa5s.times', color='#888'))
        btn_close.setIconSize(QSize(12, 12))
        btn_close.setFixedSize(28, 28)
        btn_close.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                border-radius: 14px;
            }}
            QPushButton:hover {{ background: {HOVER}; }}
        """)
        btn_close.clicked.connect(self.close)
        header.addWidget(btn_close)

        root.addLayout(header)

        mode_row = QHBoxLayout()
        mode_row.setSpacing(8)
        self.btn_mode_rules = QPushButton("Правила")
        self.btn_mode_rules.setCursor(Qt.PointingHandCursor)
        self.btn_mode_rules.clicked.connect(lambda: self._set_mode("rules"))
        self.btn_mode_laws = QPushButton("Законы")
        self.btn_mode_laws.setCursor(Qt.PointingHandCursor)
        self.btn_mode_laws.clicked.connect(lambda: self._set_mode("laws"))
        mode_row.addWidget(self.btn_mode_rules)
        mode_row.addWidget(self.btn_mode_laws)
        mode_row.addStretch()

        btn_export = QPushButton("Сохранить в .json")
        btn_export.setCursor(Qt.PointingHandCursor)
        btn_export.setStyleSheet(self._primary_btn_style())
        btn_export.clicked.connect(self._export_json)
        mode_row.addWidget(btn_export)

        root.addLayout(mode_row)

        body = QHBoxLayout()
        body.setSpacing(14)

        left = QVBoxLayout()
        left.setSpacing(8)

        list_label = QLabel("Список")
        list_label.setStyleSheet(f"color: {TEXT_GRAY}; font-size: 11px; background: transparent; border: none;")
        left.addWidget(list_label)

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(f"""
            QListWidget {{
                background: rgba(255, 255, 255, 8);
                border: 1px solid rgba(255, 255, 255, 25);
                border-radius: 10px;
                color: {TEXT_WHITE};
                padding: 6px;
                font-size: 12px;
                outline: none;
            }}
            QListWidget::item {{
                padding: 6px 8px;
                border-radius: 6px;
            }}
            QListWidget::item:hover {{ background: {HOVER}; }}
            QListWidget::item:selected {{
                background: rgba(45, 94, 255, 90);
                color: {TEXT_WHITE};
            }}
        """)
        self.list_widget.currentRowChanged.connect(self._on_select)
        left.addWidget(self.list_widget, stretch=1)

        list_buttons = QHBoxLayout()
        list_buttons.setSpacing(6)

        btn_add = QPushButton("Добавить")
        btn_add.clicked.connect(self._add_item)
        btn_add.setCursor(Qt.PointingHandCursor)
        btn_add.setStyleSheet(self._small_btn_style())
        list_buttons.addWidget(btn_add)

        btn_remove = QPushButton("Удалить")
        btn_remove.clicked.connect(self._remove_item)
        btn_remove.setCursor(Qt.PointingHandCursor)
        btn_remove.setStyleSheet(self._small_btn_style())
        list_buttons.addWidget(btn_remove)

        left.addLayout(list_buttons)

        left_widget = QWidget()
        left_widget.setLayout(left)
        left_widget.setFixedWidth(280)
        body.addWidget(left_widget)

        right = QVBoxLayout()
        right.setSpacing(8)

        right.addWidget(self._label("ID"))
        self.field_id = QLineEdit()
        self.field_id.setStyleSheet(self._input_style())
        right.addWidget(self.field_id)

        right.addWidget(self._label("Заголовок"))
        self.field_title = QLineEdit()
        self.field_title.setStyleSheet(self._input_style())
        right.addWidget(self.field_title)

        right.addWidget(self._label("Краткое описание"))
        self.field_summary = QLineEdit()
        self.field_summary.setStyleSheet(self._input_style())
        right.addWidget(self.field_summary)

        right.addWidget(self._label("Полное описание"))
        self.field_description = QTextEdit()
        self.field_description.setStyleSheet(self._textarea_style())
        self.field_description.setFixedHeight(90)
        right.addWidget(self.field_description)

        right.addWidget(self._label("Наказания (по одному на строку)"))
        self.field_punishment = QTextEdit()
        self.field_punishment.setStyleSheet(self._textarea_style())
        self.field_punishment.setFixedHeight(60)
        right.addWidget(self.field_punishment)

        right.addWidget(self._label("Исключения (по одному на строку)"))
        self.field_exceptions = QTextEdit()
        self.field_exceptions.setStyleSheet(self._textarea_style())
        self.field_exceptions.setFixedHeight(60)
        right.addWidget(self.field_exceptions)

        right.addStretch()

        save_row = QHBoxLayout()
        save_row.setSpacing(8)

        btn_apply = QPushButton("Применить изменения")
        btn_apply.setCursor(Qt.PointingHandCursor)
        btn_apply.setStyleSheet(self._primary_btn_style())
        btn_apply.clicked.connect(self._apply_item)
        save_row.addWidget(btn_apply)
        save_row.addStretch()

        right.addLayout(save_row)

        right_widget = QWidget()
        right_widget.setLayout(right)
        body.addWidget(right_widget, stretch=1)

        root.addLayout(body, stretch=1)

        self._update_mode_buttons()

    def _label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {TEXT_GRAY}; font-size: 11px; background: transparent; border: none;")
        return lbl

    def _input_style(self):
        return f"""
            QLineEdit {{
                background: rgba(255, 255, 255, 12);
                border: 1px solid rgba(255, 255, 255, 30);
                border-radius: 8px;
                padding: 8px 12px;
                color: {TEXT_WHITE};
                font-size: 13px;
            }}
            QLineEdit:focus {{ border: 1px solid {ACCENT}; }}
        """

    def _textarea_style(self):
        return f"""
            QTextEdit {{
                background: rgba(255, 255, 255, 12);
                border: 1px solid rgba(255, 255, 255, 30);
                border-radius: 8px;
                padding: 8px 12px;
                color: {TEXT_WHITE};
                font-size: 13px;
            }}
            QTextEdit:focus {{ border: 1px solid {ACCENT}; }}
        """

    def _small_btn_style(self):
        return f"""
            QPushButton {{
                background: rgba(255, 255, 255, 15);
                color: {TEXT_WHITE};
                border: 1px solid rgba(255, 255, 255, 30);
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 12px;
            }}
            QPushButton:hover {{ background: rgba(255, 255, 255, 30); }}
        """

    def _primary_btn_style(self):
        return f"""
            QPushButton {{
                background: {ACCENT};
                color: {TEXT_WHITE};
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background: {ACCENT_LIGHT}; }}
        """

    def _update_mode_buttons(self):
        active = f"""
            QPushButton {{
                background: {ACCENT};
                color: {TEXT_WHITE};
                border: none;
                border-radius: 8px;
                padding: 6px 18px;
                font-size: 13px;
                font-weight: bold;
            }}
        """
        inactive = f"""
            QPushButton {{
                background: rgba(255, 255, 255, 12);
                color: {TEXT_GRAY};
                border: 1px solid rgba(255, 255, 255, 25);
                border-radius: 8px;
                padding: 6px 18px;
                font-size: 13px;
            }}
            QPushButton:hover {{ background: rgba(255, 255, 255, 25); }}
        """
        if self._mode == "rules":
            self.btn_mode_rules.setStyleSheet(active)
            self.btn_mode_laws.setStyleSheet(inactive)
        else:
            self.btn_mode_rules.setStyleSheet(inactive)
            self.btn_mode_laws.setStyleSheet(active)

    def _new_profile(self):
        self._data = {"rules": [], "laws": []}
        self._current_index = -1
        self._refresh_list()
        self._clear_form()
        print("Создан новый профиль (пустой)")

    def _set_mode(self, mode):
        self._mode = mode
        self._current_index = -1
        self._update_mode_buttons()
        self._refresh_list()
        self._clear_form()

    def _refresh_list(self):
        self.list_widget.clear()
        items = self._data.get(self._mode, [])
        for item in items:
            text = f"{item.get('id', '?')}  {item.get('title', '')}"
            list_item = QListWidgetItem(text)
            self.list_widget.addItem(list_item)

    def _clear_form(self):
        self.field_id.clear()
        self.field_title.clear()
        self.field_summary.clear()
        self.field_description.clear()
        self.field_punishment.clear()
        self.field_exceptions.clear()

    def _on_select(self, index):
        if index < 0:
            return
        items = self._data.get(self._mode, [])
        if index >= len(items):
            return
        self._current_index = index
        item = items[index]
        self.field_id.setText(item.get("id", ""))
        self.field_title.setText(item.get("title", ""))
        self.field_summary.setText(item.get("summary", ""))
        self.field_description.setPlainText(item.get("description", ""))
        self.field_punishment.setPlainText("\n".join(item.get("punishment", [])))
        self.field_exceptions.setPlainText("\n".join(item.get("exceptions", [])))

    def _add_item(self):
        new_item = {
            "id": "",
            "title": "Новый элемент",
            "summary": "",
            "description": "",
            "punishment": [],
            "exceptions": [],
        }
        self._data.setdefault(self._mode, []).append(new_item)
        self._refresh_list()
        self.list_widget.setCurrentRow(len(self._data[self._mode]) - 1)

    def _remove_item(self):
        if self._current_index < 0:
            return
        items = self._data.get(self._mode, [])
        if self._current_index >= len(items):
            return
        del items[self._current_index]
        self._current_index = -1
        self._refresh_list()
        self._clear_form()

    def _apply_item(self):
        if self._current_index < 0:
            print("Не выбран элемент")
            return
        items = self._data.get(self._mode, [])
        if self._current_index >= len(items):
            return

        item = {
            "id": self.field_id.text().strip(),
            "title": self.field_title.text().strip(),
            "summary": self.field_summary.text().strip(),
            "description": self.field_description.toPlainText().strip(),
            "punishment": [line.strip() for line in self.field_punishment.toPlainText().split("\n") if line.strip()],
            "exceptions": [line.strip() for line in self.field_exceptions.toPlainText().split("\n") if line.strip()],
        }
        items[self._current_index] = item
        self._refresh_list()
        self.list_widget.setCurrentRow(self._current_index)
        print(f"Применено: {item.get('id', '')}")

    def _export_json(self):
        ps_script = (
            "Add-Type -AssemblyName System.Windows.Forms;"
            "$f = New-Object System.Windows.Forms.SaveFileDialog;"
            "$f.Filter = 'JSON files (*.json)|*.json';"
            "$f.FileName = 'data.json';"
            "$f.Title = 'Куда сохранить файл правил';"
            "if ($f.ShowDialog() -eq 'OK') { Write-Output $f.FileName }"
        )
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_script],
                capture_output=True, text=True, timeout=120,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
            )
            path = result.stdout.strip()
        except Exception as e:
            print(f"Ошибка диалога: {e}")
            return

        if not path:
            print("Сохранение отменено")
            return

        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
            print(f"Сохранено: {path}")
            self.saved.emit(path)
        except Exception as e:
            print(f"Ошибка сохранения: {e}")

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
            print(f"Builder blur error: {e}")

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

    def closeEvent(self, event):
        self._bg_timer.stop()
        super().closeEvent(event)