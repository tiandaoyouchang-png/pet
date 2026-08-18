#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Apple-inspired UI shell for Momo Desktop Pet.

This module intentionally leaves the animation/behaviour engine in pixar_pet.py
untouched. It subclasses the existing window and replaces only the presentation
layer: speech bubbles, menus, status popover and preferences.
"""
import sys

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QAction, QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QSlider,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

import pixar_pet as core

ACCENT = "#ff5d8f"
TEXT = "#1d1d1f"
SECONDARY = "#6e6e73"
BORDER = "rgba(60,60,67,0.16)"
SURFACE = "rgba(255,255,255,0.92)"


def _font(size=13, weight=QFont.Normal):
    f = QFont("SF Pro Display")
    if not f.exactMatch():
        f = QFont("PingFang SC")
    f.setPixelSize(size)
    f.setWeight(weight)
    return f


def _menu_style():
    return f"""
        QMenu {{
            background: rgba(250, 250, 252, 245);
            border: 1px solid {BORDER};
            border-radius: 12px;
            padding: 6px;
            color: {TEXT};
            font-size: 13px;
        }}
        QMenu::item {{
            padding: 7px 28px 7px 12px;
            border-radius: 7px;
        }}
        QMenu::item:selected {{
            background: rgba(10, 132, 255, 0.12);
        }}
        QMenu::separator {{
            height: 1px;
            background: rgba(60,60,67,0.12);
            margin: 5px 8px;
        }}
    """


class AppleSpeechBubble(core.SpeechBubble):
    """Compact macOS-like speech bubble with softer typography and shadow."""

    def draw(self, p: QPainter):
        if self.t < 0.0 or not self.text:
            return
        appear = core.smoothstep(self.t / 0.18)
        fade = 1.0 if self.t < self.duration - 0.4 else core.smoothstep((self.duration - self.t) / 0.4)
        alpha = appear * fade

        font = _font(15, QFont.DemiBold)
        p.setFont(font)
        fm = p.fontMetrics()
        tw = fm.horizontalAdvance(self.text)
        max_w = core.W - 36
        bw = min(max_w, tw + 32)
        bh = 38
        bx = core.clamp(core.CX - bw / 2, 18, core.W - bw - 18)
        by = 14.0

        p.save()
        p.setOpacity(alpha)
        p.setPen(Qt.NoPen)

        # ambient shadow
        p.setBrush(QColor(0, 0, 0, 22))
        p.drawRoundedRect(QRectF(bx, by + 5, bw, bh), 18, 18)

        # translucent Apple-like surface
        grad = QLinearGradient(bx, by, bx, by + bh)
        grad.setColorAt(0.0, QColor(255, 255, 255, 246))
        grad.setColorAt(1.0, QColor(246, 246, 248, 238))
        p.setBrush(grad)
        p.setPen(QPen(QColor(255, 255, 255, 210), 1.0))
        p.drawRoundedRect(QRectF(bx, by, bw, bh), 18, 18)

        tail = QPainterPath()
        tail.moveTo(core.CX - 7, by + bh - 2)
        tail.quadTo(core.CX, by + bh + 11, core.CX + 8, by + bh - 1)
        tail.closeSubpath()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(248, 248, 250, 242))
        p.drawPath(tail)

        p.setPen(QColor(35, 35, 38))
        p.drawText(QRectF(bx + 14, by, bw - 28, bh), Qt.AlignCenter, self.text)
        p.restore()


class StatusCard(QWidget):
    """Small lightweight status card, opened from the menu bar icon."""

    def __init__(self, pet):
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.pet = pet
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setFixedSize(286, 248)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        card = QFrame()
        card.setObjectName("card")
        card.setStyleSheet(f"""
            QFrame#card {{
                background: {SURFACE};
                border: 1px solid {BORDER};
                border-radius: 18px;
            }}
            QLabel {{ color: {TEXT}; background: transparent; }}
            QPushButton {{
                background: rgba(118,118,128,0.10);
                border: 0;
                border-radius: 12px;
                padding: 9px 5px;
                color: {TEXT};
                font-size: 12px;
            }}
            QPushButton:hover {{ background: rgba(118,118,128,0.17); }}
            QPushButton:pressed {{ background: rgba(118,118,128,0.23); }}
        """)
        root.addWidget(card)

        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 16, 16, 14)
        lay.setSpacing(10)

        header = QHBoxLayout()
        self.avatar = QLabel()
        self.avatar.setFixedSize(48, 48)
        header.addWidget(self.avatar)
        names = QVBoxLayout()
        title = QLabel("Momo")
        title.setFont(_font(18, QFont.DemiBold))
        self.subtitle = QLabel("● 活跃中")
        self.subtitle.setStyleSheet("color:#34c759")
        self.subtitle.setFont(_font(12))
        names.addWidget(title)
        names.addWidget(self.subtitle)
        header.addLayout(names, 1)
        lay.addLayout(header)

        self.mood = QLabel()
        self.hunger = QLabel()
        self.energy = QLabel()
        for label in (self.mood, self.hunger, self.energy):
            label.setFont(_font(12, QFont.Medium))
            lay.addWidget(label)

        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet("background:rgba(60,60,67,0.12)")
        lay.addWidget(divider)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        for text, fn in (("🍪\n喂食", pet.feed), ("🎮\n玩耍", pet.play_ball), ("💃\n跳舞", pet.dance), ("🌙\n睡觉", pet.toggle_sleep)):
            b = QPushButton(text)
            b.setFixedHeight(50)
            b.clicked.connect(lambda checked=False, f=fn: self._run(f))
            actions.addWidget(b)
        lay.addLayout(actions)
        self.refresh()

    def _run(self, fn):
        fn()
        self.refresh()

    def refresh(self):
        pix = QPixmap(80, 96)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)
        p.setWindow(56, 90, 248, 300)
        p.setViewport(0, 0, 48, 58)
        self.pet.character.draw(p)
        p.end()
        self.avatar.setPixmap(pix.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        n = self.pet.needs
        self.mood.setText(f"♥  心情值        {round(n['mood'] * 100):d} / 100")
        self.hunger.setText(f"◐  饱食度        {round(n['hunger'] * 100):d} / 100")
        self.energy.setText(f"⚡  精力值        {round(n['energy'] * 100):d} / 100")
        sleeping = self.pet.character.mode == "sleep"
        self.subtitle.setText("● 睡眠中" if sleeping else "● 活跃中")
        self.subtitle.setStyleSheet("color:#8e8e93" if sleeping else "color:#34c759")


class PreferencesDialog(QDialog):
    """A deliberately small settings surface instead of a full control centre."""

    def __init__(self, pet):
        super().__init__(pet)
        self.pet = pet
        self.setWindowTitle("Momo 偏好设置")
        self.setMinimumSize(430, 340)
        self.setStyleSheet(f"""
            QDialog {{ background:#f5f5f7; color:{TEXT}; }}
            QLabel {{ color:{TEXT}; }}
            QFrame#group {{ background:white; border:1px solid {BORDER}; border-radius:14px; }}
            QSlider::groove:horizontal {{ height:4px; background:#dedee3; border-radius:2px; }}
            QSlider::sub-page:horizontal {{ background:{ACCENT}; border-radius:2px; }}
            QSlider::handle:horizontal {{ width:16px; margin:-6px 0; background:white; border:1px solid #c7c7cc; border-radius:8px; }}
            QPushButton {{ background:#e7e7eb; border:0; border-radius:9px; padding:8px 14px; }}
            QPushButton:hover {{ background:#dcdce1; }}
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 22)
        root.setSpacing(16)

        title = QLabel("Momo 设置")
        title.setFont(_font(22, QFont.DemiBold))
        root.addWidget(title)
        sub = QLabel("保持轻量，只放真正影响桌宠体验的设置。")
        sub.setStyleSheet(f"color:{SECONDARY}")
        root.addWidget(sub)

        group = QFrame()
        group.setObjectName("group")
        gl = QVBoxLayout(group)
        gl.setContentsMargins(16, 14, 16, 14)
        gl.setSpacing(14)

        row = QHBoxLayout()
        row.addWidget(QLabel("宠物透明度"))
        self.opacity = QSlider(Qt.Horizontal)
        self.opacity.setRange(55, 100)
        self.opacity.setValue(round(pet.windowOpacity() * 100))
        self.opacity.valueChanged.connect(lambda v: pet.setWindowOpacity(v / 100.0))
        row.addWidget(self.opacity, 1)
        gl.addLayout(row)

        self.always_on_top = QCheckBox("始终置顶")
        self.always_on_top.setChecked(True)
        self.always_on_top.setEnabled(False)
        gl.addWidget(self.always_on_top)

        note = QLabel("Momo 仍会保持跨 Space / 全屏可见，并继续不抢键盘焦点。")
        note.setWordWrap(True)
        note.setStyleSheet(f"color:{SECONDARY}; font-size:12px")
        gl.addWidget(note)
        root.addWidget(group)

        close = QPushButton("完成")
        close.clicked.connect(self.accept)
        root.addWidget(close, 0, Qt.AlignRight)


class ApplePetWindow(core.PetWindow):
    def __init__(self, app):
        self.status_card = None
        self.preferences = None
        super().__init__(app)
        self.bubble = AppleSpeechBubble()
        self.setWindowOpacity(0.98)

    def setup_tray(self):
        pix = QPixmap(80, 96)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)
        p.setWindow(56, 90, 248, 300)
        p.setViewport(0, 0, 80, 96)
        self.character.draw(p)
        p.end()

        self.tray = QSystemTrayIcon(QIcon(pix), self)
        self.tray.setToolTip("Momo · 点击查看状态")
        menu = self._build_menu()
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_apple_tray)
        self.tray.show()

    def _build_menu(self):
        menu = QMenu()
        menu.setStyleSheet(_menu_style())

        status = QAction("Momo 状态", self)
        status.triggered.connect(self.show_status_card)
        menu.addAction(status)
        menu.addSeparator()

        feed = QAction("🍪  喂小饼干", self)
        ball = QAction("🎮  扔皮球", self)
        dance = QAction("💃  跳支舞", self)
        sleep = QAction("🌙  睡觉 / 叫醒", self)
        feed.triggered.connect(self.feed)
        ball.triggered.connect(self.play_ball)
        dance.triggered.connect(self.dance)
        sleep.triggered.connect(self.toggle_sleep)
        for action in (feed, ball, dance, sleep):
            menu.addAction(action)

        menu.addSeparator()
        settings = QAction("偏好设置…", self)
        settings.triggered.connect(self.show_preferences)
        menu.addAction(settings)
        menu.addSeparator()
        quit_action = QAction("退出 Momo", self)
        quit_action.triggered.connect(self.quit)
        menu.addAction(quit_action)
        return menu

    def _on_apple_tray(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show_status_card()

    def show_status_card(self):
        if self.status_card is None:
            self.status_card = StatusCard(self)
        self.status_card.refresh()
        cursor = self.app.primaryScreen().availableGeometry().center()
        try:
            from PySide6.QtGui import QCursor
            cursor = QCursor.pos()
        except Exception:
            pass
        x = cursor.x() - self.status_card.width() // 2
        y = cursor.y() + 10
        screen = self.app.screenAt(cursor) or self.app.primaryScreen()
        area = screen.availableGeometry()
        x = max(area.left() + 8, min(x, area.right() - self.status_card.width() - 8))
        y = max(area.top() + 8, min(y, area.bottom() - self.status_card.height() - 8))
        self.status_card.move(x, y)
        self.status_card.show()
        self.status_card.raise_()

    def show_preferences(self):
        if self.preferences is None:
            self.preferences = PreferencesDialog(self)
        self.preferences.show()
        self.preferences.raise_()
        self.preferences.activateWindow()

    def show_context_menu(self, global_pos):
        menu = self._build_menu()
        menu.setParent(self)
        menu.setAttribute(Qt.WA_ShowWithoutActivating, True)
        menu.exec(global_pos)


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
