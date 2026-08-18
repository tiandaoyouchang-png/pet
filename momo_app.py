#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Apple/macOS presentation layer for Momo Desktop Pet."""
import sys
import time

from PySide6.QtCore import QRectF, QTimer, Qt
from PySide6.QtGui import (
    QAction, QColor, QCursor, QFont, QIcon, QLinearGradient, QPainter,
    QPainterPath, QPalette, QPen, QPixmap,
)
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
        self.hud_visible_until = time.monotonic() + 5.0
        super().__init__(app)
        self.bubble = AppleSpeechBubble(self)
        self._connect_system_appearance()
        self.apply_ui_state(save=False)
        self.bubble.show(core.say("start"), 3.6)
        self.reveal_hud(5.0)
        self.ui_timer = QTimer(self)
        self.ui_timer.timeout.connect(self.update_dynamic_ui)
        self.ui_timer.start(1200)

    # ---------- persistence ----------
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
                # Migration from the first Apple UI prototype.
                if "hud_mode" not in saved_ui and "hud_enabled" in saved_ui:
                    self.ui_state["hud_mode"] = "smart" if saved_ui.get("hud_enabled") else "off"
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

    # ---------- theme ----------
    def _connect_system_appearance(self):
        try:
            signal = getattr(self.app.styleHints(), "colorSchemeChanged", None)
            if signal is not None:
                signal.connect(self._on_system_appearance_changed)
        except Exception:
            pass

    def _on_system_appearance_changed(self, *args):
        if self.ui_state.get("theme_mode") == "system":
            self.apply_ui_state(save=False)

    def effective_theme_name(self):
        mode = self.ui_state.get("theme_mode", "system")
        if mode == "dark":
            return "深色"
        if mode == "light":
            return "浅色"
        try:
            scheme_fn = getattr(self.app.styleHints(), "colorScheme", None)
            if scheme_fn is not None:
                scheme = scheme_fn()
                if scheme == Qt.ColorScheme.Dark:
                    return "深色"
                if scheme == Qt.ColorScheme.Light:
                    return "浅色"
        except Exception:
            pass
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
        if self.ui_state.get("hud_mode") not in ("smart", "always", "off"):
            self.ui_state["hud_mode"] = "smart"
        self.setWindowOpacity(opacity)
        if not self.ui_state.get("speech_enabled", True):
            self.bubble.t = -1.0
        self._apply_menu_style()
        self._refresh_menu_actions()
        self.refresh_tray_icon()
        self.refresh_tray_tooltip()
        if self.status_card is not None:
            self.status_card.refresh()
        if self.preferences is not None and self.preferences.isVisible():
            self.preferences.sync_from_pet()
        self.update()
        if save:
            self.save_state()

    # ---------- tray icon ----------
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

    def make_template_tray_icon(self):
        """Minimal egg silhouette; marked as a mask so macOS adapts it to the menu bar."""
        pix = QPixmap(44, 44)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)
        egg = QPainterPath()
        egg.moveTo(22, 5)
        egg.cubicTo(13, 5, 7, 16, 8, 27)
        egg.cubicTo(9, 36, 14, 40, 22, 40)
        egg.cubicTo(30, 40, 35, 36, 36, 27)
        egg.cubicTo(37, 16, 31, 5, 22, 5)
        egg.closeSubpath()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0))
        p.drawPath(egg)
        p.setCompositionMode(QPainter.CompositionMode_Clear)
        p.drawEllipse(QRectF(15, 19, 4, 6))
        p.drawEllipse(QRectF(25, 19, 4, 6))
        p.end()
        pix.setDevicePixelRatio(2.0)
        icon = QIcon(pix)
        icon.setIsMask(True)
        return icon

    def refresh_tray_icon(self):
        if not hasattr(self, "tray"):
            return
        if sys.platform == "darwin":
            self.tray.setIcon(self.make_template_tray_icon())
        else:
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

    # ---------- HUD ----------
    def reveal_hud(self, seconds=4.0):
        if self.ui_state.get("hud_mode", "smart") == "off":
            return
        self.hud_visible_until = max(self.hud_visible_until, time.monotonic() + seconds)
        self.update()

    def should_draw_hud(self):
        mode = self.ui_state.get("hud_mode", "smart")
        if mode == "off":
            return False
        if mode == "always":
            return True
        return time.monotonic() < self.hud_visible_until

    # ---------- dynamic UI ----------
    def update_dynamic_ui(self):
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
        self.reveal_hud(4.0)
        self._refresh_menu_actions()
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
            self.reveal_hud(4.0)
        self._refresh_menu_actions()
        self.update_dynamic_ui()
        self.save_state()

    # ---------- native-looking menu ----------
    def setup_tray(self):
        self.tray = QSystemTrayIcon(self)
        self.tray_menu = self._build_menu()
        self.tray.setContextMenu(self.tray_menu)
        self.tray.activated.connect(self._on_apple_tray)
        self.refresh_tray_icon()
        self.refresh_tray_tooltip()
        self.tray.show()

    def _menu_style(self):
        if sys.platform == "darwin":
            # Let Cocoa/Qt use the platform menu appearance instead of overriding it with QSS.
            return ""
        colors = self.current_colors()
        return """
            QMenu {{ background:{}; border:1px solid {}; border-radius:14px; padding:6px; color:{}; font-size:13px; }}
            QMenu::item {{ padding:8px 30px 8px 12px; border-radius:8px; margin:1px 0; }}
            QMenu::item:selected {{ background:{}; }}
            QMenu::separator {{ height:1px; background:{}; margin:6px 8px; }}
        """.format(css(colors["surface"]), css(colors["border"]), css(colors["text"]), css(colors["menu_hover"]), css(colors["hairline"]))

    def _apply_menu_style(self):
        if self.tray_menu is not None:
            self.tray_menu.setStyleSheet(self._menu_style())

    def _build_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet(self._menu_style())
        menu.setAttribute(Qt.WA_ShowWithoutActivating, True)

        self.action_status = QAction("Momo 状态", self)
        self.action_status.triggered.connect(self.show_status_card)
        self.action_visibility = QAction("隐藏 Momo", self)
        self.action_visibility.triggered.connect(self.toggle_visibility)
        self.action_recall = QAction("召回到当前屏幕", self)
        self.action_recall.triggered.connect(self.recall_to_cursor_screen)
        menu.addAction(self.action_status)
        menu.addAction(self.action_visibility)
        menu.addAction(self.action_recall)
        menu.addSeparator()

        self.action_feed = QAction("喂小饼干", self)
        self.action_ball = QAction("扔皮球", self)
        self.action_dance = QAction("跳支舞", self)
        self.action_sleep = QAction("让 Momo 睡觉", self)
        self.action_feed.triggered.connect(self.feed)
        self.action_ball.triggered.connect(self.play_ball)
        self.action_dance.triggered.connect(self.dance)
        self.action_sleep.triggered.connect(self.toggle_sleep)
        for action in (self.action_feed, self.action_ball, self.action_dance, self.action_sleep):
            menu.addAction(action)
        menu.addSeparator()

        self.action_preferences = QAction("偏好设置…", self)
        self.action_preferences.triggered.connect(self.show_preferences)
        self.action_about = QAction("关于 Momo", self)
        self.action_about.triggered.connect(self.show_about)
        menu.addAction(self.action_preferences)
        menu.addAction(self.action_about)
        menu.addSeparator()
        self.action_quit = QAction("退出 Momo", self)
        self.action_quit.triggered.connect(self.quit)
        menu.addAction(self.action_quit)
        menu.aboutToShow.connect(self._refresh_menu_actions)
        return menu

    def _refresh_menu_actions(self):
        if self.tray_menu is None:
            return
        self.action_visibility.setText("显示 Momo" if self.pet_hidden else "隐藏 Momo")
        self.action_sleep.setText("叫醒 Momo" if self.character.mode == "sleep" else "让 Momo 睡觉")
        self.action_recall.setEnabled(True)

    def _on_apple_tray(self, reason):
        if reason != QSystemTrayIcon.ActivationReason.Trigger:
            return
        if self.pet_hidden:
            self.recall_to_cursor_screen()
        if self.status_card is not None and self.status_card.isVisible():
            self.status_card.hide()
        else:
            self.show_status_card()

    def show_context_menu(self, global_pos):
        self._refresh_menu_actions()
        self.tray_menu.exec(global_pos)

    # ---------- popover / preferences ----------
    def _status_anchor(self):
        try:
            geometry = self.tray.geometry()
            if geometry.isValid() and not geometry.isEmpty():
                return geometry.center(), geometry
        except Exception:
            pass
        cursor = QCursor.pos()
        return cursor, QRectF(cursor.x(), cursor.y(), 1, 1).toRect()

    def show_status_card(self):
        if self.status_card is None:
            self.status_card = StatusCard(self)
        self.status_card.refresh()
        anchor, tray_rect = self._status_anchor()
        screen = self.app.screenAt(anchor) or self.app.primaryScreen()
        area = screen.availableGeometry()
        x = anchor.x() - self.status_card.width() // 2
        below = tray_rect.bottom() + 8
        above = tray_rect.top() - self.status_card.height() - 8
        y = below if below + self.status_card.height() <= area.bottom() else above
        x = max(area.left() + 8, min(x, area.right() - self.status_card.width() - 8))
        y = max(area.top() + 8, min(y, area.bottom() - self.status_card.height() - 8))
        self.status_card.move(x, y)
        self.status_card.show()
        self.status_card.raise_()

    def show_preferences(self):
        if self.status_card is not None:
            self.status_card.hide()
        if self.preferences is None:
            self.preferences = PreferencesDialog(self)
        self.preferences.sync_from_pet()
        self.preferences.show()
        self.preferences.raise_()
        self.preferences.activateWindow()

    def show_about(self):
        QMessageBox.information(
            self, "关于 Momo",
            "Momo Desktop Pet\n\n保留鸡蛋形象与 60 FPS 行为动画，\nUI 按 Apple/macOS 的轻透、克制和低打扰方向重新设计。",
        )

    # ---------- interaction hooks ----------
    def feed(self):
        super().feed()
        self.reveal_hud(4.5)
        self.update_dynamic_ui()

    def play_ball(self):
        super().play_ball()
        self.reveal_hud(4.5)
        self.update_dynamic_ui()

    def dance(self, highfive=False):
        super().dance(highfive=highfive)
        self.reveal_hud(4.5)
        self.update_dynamic_ui()

    def toggle_sleep(self):
        super().toggle_sleep()
        self.reveal_hud(4.5)
        self._refresh_menu_actions()
        self.update_dynamic_ui()

    def wake(self):
        super().wake()
        self.reveal_hud(4.5)
        self._refresh_menu_actions()
        self.update_dynamic_ui()

    def poke(self):
        super().poke()
        self.reveal_hud(4.0)
        self.update_dynamic_ui()

    def mousePressEvent(self, event):
        self.reveal_hud(3.5)
        super().mousePressEvent(event)

    def wheelEvent(self, event):
        self.reveal_hud(3.5)
        super().wheelEvent(event)

    # ---------- paint ----------
    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.should_draw_hud():
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
