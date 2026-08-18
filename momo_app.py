#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Apple/macOS presentation layer for Momo Desktop Pet."""
import sys

from PySide6.QtCore import QRectF, QTimer, Qt
from PySide6.QtGui import QAction, QCursor, QFont, QIcon, QLinearGradient, QPainter, QPainterPath, QPalette, QPen, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon

import pixar_pet as core
from momo_ui import DARK, DEFAULT_UI, LIGHT, MODE_LABELS, PreferencesDialog, StatusCard, css, qcolor, ui_font


class AppleSpeechBubble(core.SpeechBubble):
    def __init__(self, pet):
        super().__init__()
        self.pet = pet

    def show(self, text, duration=3.2):
        if not self.pet.ui_state.get("speech_enabled", True):
            self.t = -1.0
            return
        scale = float(self.pet.ui_state.get("bubble_scale", 1.0))
        super().show(text, max(1.5, duration * scale))

    def draw(self, p: QPainter):
        if self.t < 0.0 or not self.text:
            return
        colors = self.pet.current_colors()
        appear = core.smoothstep(self.t / 0.18)
        fade = 1.0 if self.t < self.duration - 0.4 else core.smoothstep((self.duration - self.t) / 0.4)
        alpha = appear * fade
        p.setFont(ui_font(15, QFont.DemiBold))
        fm = p.fontMetrics()
        width = min(core.W - 36, fm.horizontalAdvance(self.text) + 34)
        height = 40
        x = core.clamp(core.CX - width / 2, 18, core.W - width - 18)
        y = 14.0

        p.save()
        p.setOpacity(alpha)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(qcolor(colors["chip_shadow"]))
        p.drawRoundedRect(QRectF(x, y + 5, width, height), 18, 18)
        gradient = QLinearGradient(x, y, x, y + height)
        gradient.setColorAt(0.0, qcolor(colors["surface_strong"]))
        gradient.setColorAt(1.0, qcolor(colors["surface_soft"]))
        p.setBrush(gradient)
        p.setPen(QPen(qcolor(colors["border"]), 1.0))
        p.drawRoundedRect(QRectF(x, y, width, height), 18, 18)
        tail = QPainterPath()
        tail.moveTo(core.CX - 7, y + height - 2)
        tail.quadTo(core.CX, y + height + 11, core.CX + 8, y + height - 1)
        tail.closeSubpath()
        p.setPen(Qt.NoPen)
        p.setBrush(qcolor(colors["surface_soft"]))
        p.drawPath(tail)
        p.setPen(qcolor(colors["text"]))
        p.drawText(QRectF(x + 14, y, width - 28, height), Qt.AlignCenter, self.text)
        p.restore()


class ApplePetWindow(core.PetWindow):
    def __init__(self, app):
        self.ui_state = dict(DEFAULT_UI)
        self.status_card = None
        self.preferences = None
        self.tray_menu = None
        self.pet_hidden = False
        super().__init__(app)
        self.bubble = AppleSpeechBubble(self)
        self.apply_ui_state(save=False)
        self.bubble.show(core.say("start"), 3.6)
        self.ui_timer = QTimer(self)
        self.ui_timer.timeout.connect(self.update_dynamic_ui)
        self.ui_timer.start(1200)

    def load_state(self):
        super().load_state()
        try:
            with open(core.SAVE_PATH, "r", encoding="utf-8") as handle:
                data = core.json.load(handle)
            saved_ui = data.get("ui")
            if isinstance(saved_ui, dict):
                for key in DEFAULT_UI:
                    if key in saved_ui:
                        self.ui_state[key] = saved_ui[key]
        except Exception:
            pass

    def save_state(self):
        try:
            data = dict(self.needs)
            data["pos"] = [self.x(), self.y()]
            data["ui"] = {key: self.ui_state.get(key, value) for key, value in DEFAULT_UI.items()}
            with open(core.SAVE_PATH, "w", encoding="utf-8") as handle:
                core.json.dump(data, handle, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def effective_theme_name(self):
        mode = self.ui_state.get("theme_mode", "system")
        if mode == "dark":
            return "深色"
        if mode == "light":
            return "浅色"
        try:
            return "深色" if self.app.palette().color(QPalette.Window).lightness() < 128 else "浅色"
        except Exception:
            return "浅色"

    def current_colors(self):
        mode = self.ui_state.get("theme_mode", "system")
        if mode == "dark":
            return DARK
        if mode == "light":
            return LIGHT
        return DARK if self.effective_theme_name() == "深色" else LIGHT

    def apply_ui_state(self, save=True):
        opacity = max(0.70, min(1.0, float(self.ui_state.get("opacity", 0.98))))
        self.ui_state["opacity"] = opacity
        self.setWindowOpacity(opacity)
        if not self.ui_state.get("speech_enabled", True):
            self.bubble.t = -1.0
        self._rebuild_tray_menu()
        self.refresh_tray_icon()
        self.refresh_tray_tooltip()
        if self.status_card is not None:
            self.status_card.refresh()
        if self.preferences is not None and self.preferences.isVisible():
            self.preferences.sync_from_pet()
        self.update()
        if save:
            self.save_state()

    def make_avatar_pixmap(self, width=80, height=96):
        pix = QPixmap(width, height)
        pix.fill(Qt.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setWindow(56, 90, 248, 300)
        painter.setViewport(0, 0, width, height)
        self.character.draw(painter)
        painter.end()
        return pix

    def refresh_tray_icon(self):
        if hasattr(self, "tray"):
            self.tray.setIcon(QIcon(self.make_avatar_pixmap(48, 56)))

    def refresh_tray_tooltip(self):
        if not hasattr(self, "tray"):
            return
        if self.pet_hidden:
            self.tray.setToolTip("Momo · 已隐藏（点击可召回）")
            return
        mood = int(round(self.needs["mood"] * 100))
        hunger = int(round(self.needs["hunger"] * 100))
        mode = MODE_LABELS.get(self.character.mode, "陪伴中")
        self.tray.setToolTip("Momo · {} · 心情 {} · 饱食 {}".format(mode, mood, hunger))

    def update_dynamic_ui(self):
        self.refresh_tray_icon()
        self.refresh_tray_tooltip()
        if self.status_card is not None and self.status_card.isVisible():
            self.status_card.refresh()
        if self.preferences is not None and self.preferences.isVisible():
            self.preferences.sync_from_pet()

    def recall_to_cursor_screen(self):
        self.pet_hidden = False
        self.show()
        self.move_to_floor(animate=False)
        self._assert_always_on_top()
        self.bubble.show("我回来啦～", 2.1)
        self._rebuild_tray_menu()
        self.update_dynamic_ui()
        self.save_state()

    def toggle_visibility(self):
        self.pet_hidden = not self.pet_hidden
        if self.pet_hidden:
            self.hide()
            if self.status_card is not None:
                self.status_card.hide()
        else:
            self.show()
            self.move_to_floor(animate=False)
            self._assert_always_on_top()
            self.bubble.show("我在这里哦～", 2.1)
        self._rebuild_tray_menu()
        self.update_dynamic_ui()
        self.save_state()

    def setup_tray(self):
        self.tray = QSystemTrayIcon(QIcon(self.make_avatar_pixmap()), self)
        self._rebuild_tray_menu()
        self.tray.activated.connect(self._on_apple_tray)
        self.refresh_tray_tooltip()
        self.tray.show()

    def _menu_style(self):
        colors = self.current_colors()
        return """
            QMenu {{ background:{}; border:1px solid {}; border-radius:14px; padding:6px; color:{}; font-size:13px; }}
            QMenu::item {{ padding:8px 30px 8px 12px; border-radius:8px; margin:1px 0; }}
            QMenu::item:selected {{ background:{}; }}
            QMenu::separator {{ height:1px; background:{}; margin:6px 8px; }}
        """.format(css(colors["surface"]), css(colors["border"]), css(colors["text"]), css(colors["menu_hover"]), css(colors["hairline"]))

    def _build_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet(self._menu_style())
        menu.setAttribute(Qt.WA_ShowWithoutActivating, True)
        status = QAction("Momo 状态", self)
        status.triggered.connect(self.show_status_card)
        menu.addAction(status)
        visibility = QAction("显示 Momo" if self.pet_hidden else "隐藏 Momo", self)
        visibility.triggered.connect(self.toggle_visibility)
        menu.addAction(visibility)
        recall = QAction("召回到当前屏幕", self)
        recall.triggered.connect(self.recall_to_cursor_screen)
        menu.addAction(recall)
        menu.addSeparator()
        feed = QAction("🍪  喂小饼干", self)
        ball = QAction("🎮  扔皮球", self)
        dance = QAction("💃  跳支舞", self)
        sleep = QAction("🌙  叫醒 Momo" if self.character.mode == "sleep" else "🌙  让 Momo 睡觉", self)
        feed.triggered.connect(self.feed)
        ball.triggered.connect(self.play_ball)
        dance.triggered.connect(self.dance)
        sleep.triggered.connect(self.toggle_sleep)
        for action in (feed, ball, dance, sleep):
            menu.addAction(action)
        menu.addSeparator()
        preferences = QAction("偏好设置…", self)
        preferences.triggered.connect(self.show_preferences)
        menu.addAction(preferences)
        about = QAction("关于 Momo", self)
        about.triggered.connect(self.show_about)
        menu.addAction(about)
        menu.addSeparator()
        quit_action = QAction("退出 Momo", self)
        quit_action.triggered.connect(self.quit)
        menu.addAction(quit_action)
        return menu

    def _rebuild_tray_menu(self):
        if hasattr(self, "tray"):
            self.tray_menu = self._build_menu()
            self.tray.setContextMenu(self.tray_menu)

    def _on_apple_tray(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.pet_hidden:
                self.recall_to_cursor_screen()
            self.show_status_card()

    def show_context_menu(self, global_pos):
        menu = self._build_menu()
        menu.exec(global_pos)

    def show_status_card(self):
        if self.status_card is None:
            self.status_card = StatusCard(self)
        self.status_card.refresh()
        cursor = QCursor.pos()
        screen = self.app.screenAt(cursor) or self.app.primaryScreen()
        area = screen.availableGeometry()
        x = cursor.x() - self.status_card.width() // 2
        y = cursor.y() + 12
        x = max(area.left() + 8, min(x, area.right() - self.status_card.width() - 8))
        y = max(area.top() + 8, min(y, area.bottom() - self.status_card.height() - 8))
        self.status_card.move(x, y)
        self.status_card.show()
        self.status_card.raise_()

    def show_preferences(self):
        if self.preferences is None:
            self.preferences = PreferencesDialog(self)
        self.preferences.sync_from_pet()
        self.preferences.show()
        self.preferences.raise_()
        self.preferences.activateWindow()

    def show_about(self):
        QMessageBox.information(self, "关于 Momo", "Momo Desktop Pet\n\n保留鸡蛋形象与 60 FPS 行为动画，\nUI 按 Apple/macOS 的轻透、克制和低打扰方向重新设计。")

    def feed(self):
        super().feed()
        self.update_dynamic_ui()

    def play_ball(self):
        super().play_ball()
        self.update_dynamic_ui()

    def dance(self, highfive=False):
        super().dance(highfive=highfive)
        self.update_dynamic_ui()

    def toggle_sleep(self):
        super().toggle_sleep()
        self._rebuild_tray_menu()
        self.update_dynamic_ui()

    def wake(self):
        super().wake()
        self._rebuild_tray_menu()
        self.update_dynamic_ui()

    def poke(self):
        super().poke()
        self.update_dynamic_ui()

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.ui_state.get("hud_enabled", True):
            return
        colors = self.current_colors()
        mood = int(round(self.needs["mood"] * 100))
        text = "♥  心情值  {} / 100".format(mood)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setFont(ui_font(13, QFont.DemiBold))
        width = painter.fontMetrics().horizontalAdvance(text) + 28
        height = 32
        x = core.clamp(core.CX - width / 2, 24, core.W - width - 24)
        y = 72.0
        painter.setPen(Qt.NoPen)
        painter.setBrush(qcolor(colors["chip_shadow"]))
        painter.drawRoundedRect(QRectF(x, y + 4, width, height), 16, 16)
        gradient = QLinearGradient(x, y, x, y + height)
        gradient.setColorAt(0.0, qcolor(colors["chip"]))
        gradient.setColorAt(1.0, qcolor(colors["surface_soft"]))
        painter.setBrush(gradient)
        painter.setPen(QPen(qcolor(colors["border"]), 1.0))
        painter.drawRoundedRect(QRectF(x, y, width, height), 16, 16)
        painter.setPen(qcolor(colors["text"]))
        painter.drawText(QRectF(x + 14, y, width - 28, height), Qt.AlignCenter, text)
        painter.end()

    def quit(self):
        self.save_state()
        super().quit()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(core.APP_NAME)
    app.setQuitOnLastWindowClosed(False)
    core._become_menu_bar_style_app()
    win = ApplePetWindow(app)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
