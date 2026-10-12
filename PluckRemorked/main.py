import sys
from PySide6.QtWidgets import QApplication

from core.settings import load_settings, save_settings
from core.data import load_data
from ui.floating_ball import FloatingBall
from ui.glass_panel import GlassPanel
from ui.builder import RuleBuilder


class PluckReMorked:
    def __init__(self):
        self.settings = load_settings()
        load_data(force_refresh=True, custom_path=self.settings.get("custom_data_path", ""))

        self.ball = FloatingBall(self.settings)
        self.panel = None
        self.builder = None

        self.ball.clicked.connect(self.open_panel)

    def open_panel(self, ball_pos):
        if self.panel is None:
            self.panel = GlassPanel(self.settings)
            self.panel.closed.connect(self.on_panel_closed)
            self.panel.builder_requested.connect(self.open_builder)
            print("Panel created, builder signal connected")
        self.panel.open_from(ball_pos)

    def open_builder(self):
        print("open_builder вызван")
        if self.builder is None:
            self.builder = RuleBuilder(self.settings)
            self.builder.saved.connect(self.on_builder_saved)
            print("RuleBuilder создан")
        self.builder.show()
        self.builder.raise_()
        self.builder.activateWindow()
        print("RuleBuilder показан")

    def on_builder_saved(self, path):
        self.settings["custom_data_path"] = path
        save_settings(self.settings)
        load_data(force_refresh=True, custom_path=path)

    def on_panel_closed(self):
        save_settings(self.settings)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    pluck = PluckReMorked()
    pluck.ball.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()