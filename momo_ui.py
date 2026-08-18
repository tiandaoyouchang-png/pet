# -*- coding: utf-8 -*-
"""Reusable Apple-style UI components for Momo Desktop Pet."""
from typing import Dict, Tuple, Union

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase
from PySide6.QtWidgets import (
    QButtonGroup, QDialog, QFrame, QGraphicsDropShadowEffect, QGridLayout,
    QHBoxLayout, QLabel, QProgressBar, QPushButton, QSlider, QVBoxLayout, QWidget,
)

Color = Union[Tuple[int, int, int], Tuple[int, int, int, int]]

LIGHT: Dict[str, Color] = {
    "text": (29, 29, 31), "secondary": (110, 110, 115),
    "surface": (255, 255, 255, 238), "surface_soft": (248, 248, 250, 232),
    "surface_strong": (255, 255, 255, 250), "floating": (245, 245, 247, 242),
    "border": (60, 60, 67, 38), "hairline": (60, 60, 67, 24),
    "accent": (255, 93, 143), "accent_soft": (255, 93, 143, 26),
    "track": (118, 118, 128, 42), "menu_hover": (10, 132, 255, 22),
    "chip": (255, 255, 255, 234), "chip_shadow": (0, 0, 0, 18),
    "success": (52, 199, 89), "warning": (255, 159, 10), "energy": (90, 100, 255),
}

DARK: Dict[str, Color] = {
    "text": (245, 245, 247), "secondary": (174, 174, 178),
    "surface": (34, 34, 38, 240), "surface_soft": (42, 42, 46, 232),
    "surface_strong": (52, 52, 58, 250), "floating": (28, 28, 32, 242),
    "border": (255, 255, 255, 28), "hairline": (255, 255, 255, 22),
    "accent": (255, 110, 156), "accent_soft": (255, 110, 156, 38),
    "track": (118, 118, 128, 64), "menu_hover": (10, 132, 255, 34),
    "chip": (46, 46, 50, 236), "chip_shadow": (0, 0, 0, 36),
    "success": (48, 209, 88), "warning": (255, 179, 64), "energy": (111, 133, 255),
}

MODE_LABELS = {
    "idle": "悠闲待机", "wander": "四处溜达", "glance": "东张西望",
    "stretch": "伸懒腰", "yawn": "打哈欠", "daydream": "发呆幻想",
    "dance": "快乐跳舞", "sleep": "安静睡觉", "held": "被抱起来",
    "pet": "被抚摸中", "eat": "开心吃点心", "ball": "追皮球",
    "wave": "挥手互动", "land": "落地缓冲", "hungry": "肚子饿啦",
}

DEFAULT_UI = {
    "theme_mode": "system",
    "opacity": 0.98,
    "bubble_scale": 1.0,
    "speech_enabled": True,
    "hud_mode": "smart",
}


def css(color: Color) -> str:
    if len(color) == 3:
        return "rgb({}, {}, {})".format(*color)
    return "rgba({}, {}, {}, {})".format(*color)


def qcolor(color: Color) -> QColor:
    return QColor(*color)


def ui_font(size=13, weight=QFont.Normal):
    font = QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont)
    font.setPointSizeF(max(8.5, float(size) * 0.78))
    font.setWeight(weight)
    return font


def add_shadow(widget: QWidget, alpha=28, blur=30, y=8):
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setOffset(0, y)
    effect.setColor(QColor(0, 0, 0, alpha))
    widget.setGraphicsEffect(effect)


class MetricRow(QWidget):
    def __init__(self, title, icon, accent, parent=None):
        super().__init__(parent)
        self.accent = accent
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(4)
        top = QHBoxLayout()
        self.title = QLabel("{}  {}".format(icon, title))
        self.title.setFont(ui_font(12, QFont.Medium))
        self.value = QLabel("0 / 100")
        self.value.setFont(ui_font(11, QFont.DemiBold))
        top.addWidget(self.title)
        top.addStretch(1)
        top.addWidget(self.value)
        root.addLayout(top)
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(8)
        root.addWidget(self.bar)

    def set_value(self, value):
        value = max(0, min(100, int(round(value))))
        self.bar.setValue(value)
        self.value.setText("{} / 100".format(value))

    def apply_theme(self, colors):
        self.title.setStyleSheet("color:{}".format(css(colors["text"])))
        self.value.setStyleSheet("color:{}".format(css(colors["secondary"])))
        self.bar.setStyleSheet("""
            QProgressBar {{ border:0; border-radius:4px; background:{}; }}
            QProgressBar::chunk {{ border-radius:4px; background:{}; }}
        """.format(css(colors["track"]), css(self.accent)))


class StatusCard(QWidget):
    def __init__(self, pet):
        super().__init__(None, Qt.Popup | Qt.FramelessWindowHint)
        self.pet = pet
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedSize(326, 382)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        self.card = QFrame()
        self.card.setObjectName("card")
        add_shadow(self.card, alpha=34, blur=36, y=10)
        root.addWidget(self.card)

        lay = QVBoxLayout(self.card)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(12)

        header = QHBoxLayout()
        header.setSpacing(12)
        self.avatar = QLabel()
        self.avatar.setFixedSize(54, 54)
        header.addWidget(self.avatar)
        names = QVBoxLayout()
        names.setSpacing(2)
        self.title = QLabel("Momo")
        self.title.setFont(ui_font(20, QFont.DemiBold))
        self.subtitle = QLabel("● 活跃中")
        self.subtitle.setFont(ui_font(12, QFont.Medium))
        self.mode = QLabel("悠闲待机")
        self.mode.setFont(ui_font(11))
        names.addWidget(self.title)
        names.addWidget(self.subtitle)
        names.addWidget(self.mode)
        header.addLayout(names, 1)
        lay.addLayout(header)

        self.mood = MetricRow("心情值", "♥", LIGHT["accent"])
        self.hunger = MetricRow("饱食度", "◐", LIGHT["warning"])
        self.energy = MetricRow("精力值", "⚡", LIGHT["energy"])
        for row in (self.mood, self.hunger, self.energy):
            lay.addWidget(row)

        divider = QFrame()
        divider.setObjectName("divider")
        divider.setFixedHeight(1)
        lay.addWidget(divider)

        section = QLabel("快捷操作")
        section.setFont(ui_font(12, QFont.Medium))
        lay.addWidget(section)

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)
        actions = [
            ("🍪", "喂食", pet.feed), ("🎮", "玩耍", pet.play_ball),
            ("💃", "跳舞", pet.dance), ("🌙", "睡觉", pet.toggle_sleep),
        ]
        for idx, (icon, label, callback) in enumerate(actions):
            button = QPushButton("{}\n{}".format(icon, label))
            button.setFixedHeight(58)
            button.clicked.connect(lambda checked=False, fn=callback: self._run(fn))
            grid.addWidget(button, idx // 2, idx % 2)
        lay.addLayout(grid)

        footer = QHBoxLayout()
        self.visibility = QPushButton("隐藏")
        self.visibility.clicked.connect(pet.toggle_visibility)
        prefs = QPushButton("设置")
        prefs.clicked.connect(pet.show_preferences)
        recall = QPushButton("召回")
        recall.clicked.connect(pet.recall_to_cursor_screen)
        footer.addWidget(self.visibility)
        footer.addWidget(prefs)
        footer.addWidget(recall)
        lay.addLayout(footer)
        self.refresh()

    def _run(self, fn):
        fn()
        self.refresh()

    def apply_theme(self):
        colors = self.pet.current_colors()
        self.mood.accent = colors["accent"]
        self.hunger.accent = colors["warning"]
        self.energy.accent = colors["energy"]
        for row in (self.mood, self.hunger, self.energy):
            row.apply_theme(colors)
        self.card.setStyleSheet("""
            QFrame#card {{ background:{}; border:1px solid {}; border-radius:20px; }}
            QFrame#divider {{ background:{}; border:0; }}
            QLabel {{ background:transparent; color:{}; }}
            QPushButton {{ background:{}; color:{}; border:1px solid {}; border-radius:13px; padding:7px 9px; font-size:12px; }}
            QPushButton:hover {{ background:{}; }}
            QPushButton:pressed {{ background:{}; }}
        """.format(
            css(colors["surface"]), css(colors["border"]), css(colors["hairline"]),
            css(colors["text"]), css(colors["surface_soft"]), css(colors["text"]),
            css(colors["border"]), css(colors["surface_strong"]), css(colors["accent_soft"])))
        self.mode.setStyleSheet("color:{}".format(css(colors["secondary"])))

    def refresh(self):
        self.apply_theme()
        self.avatar.setPixmap(self.pet.make_avatar_pixmap(70, 84).scaled(
            54, 54, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        needs = self.pet.needs
        self.mood.set_value(needs["mood"] * 100)
        self.hunger.set_value(needs["hunger"] * 100)
        self.energy.set_value(needs["energy"] * 100)
        sleeping = self.pet.character.mode == "sleep"
        colors = self.pet.current_colors()
        status_color = colors["secondary"] if sleeping else colors["success"]
        self.subtitle.setText("● 睡眠中" if sleeping else "● 活跃中")
        self.subtitle.setStyleSheet("color:{}".format(css(status_color)))
        self.mode.setText(MODE_LABELS.get(self.pet.character.mode, "陪伴中"))
        self.visibility.setText("显示" if self.pet.pet_hidden else "隐藏")


class PreferencesDialog(QDialog):
    def __init__(self, pet):
        super().__init__(pet)
        self.pet = pet
        self.theme_buttons = {}
        self.hud_buttons = {}
        self.setWindowTitle("Momo 偏好设置")
        self.setMinimumSize(520, 590)

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 20)
        root.setSpacing(14)

        hero = QHBoxLayout()
        self.avatar = QLabel()
        self.avatar.setFixedSize(64, 64)
        hero.addWidget(self.avatar)
        titles = QVBoxLayout()
        title = QLabel("Momo 偏好设置")
        title.setFont(ui_font(24, QFont.DemiBold))
        subtitle = QLabel("只保留真正影响桌宠体验的设置。")
        subtitle.setObjectName("secondary")
        titles.addWidget(title)
        titles.addWidget(subtitle)
        hero.addLayout(titles, 1)
        root.addLayout(hero)

        appearance = self._group("外观")
        ap = appearance.layout()
        ap.addWidget(QLabel("主题模式"))
        self.theme_group = QButtonGroup(self)
        self.theme_group.setExclusive(True)
        segmented = QHBoxLayout()
        for idx, (mode, label) in enumerate((("light", "浅色"), ("dark", "深色"), ("system", "跟随系统"))):
            button = QPushButton(label)
            button.setCheckable(True)
            button.clicked.connect(lambda checked=False, m=mode: self.set_theme(m))
            self.theme_group.addButton(button, idx)
            self.theme_buttons[mode] = button
            segmented.addWidget(button)
        ap.addLayout(segmented)

        row = QHBoxLayout()
        row.addWidget(QLabel("桌宠透明度"))
        row.addStretch(1)
        self.opacity_value = QLabel()
        row.addWidget(self.opacity_value)
        ap.addLayout(row)
        self.opacity = QSlider(Qt.Horizontal)
        self.opacity.setRange(70, 100)
        self.opacity.valueChanged.connect(self.opacity_changed)
        ap.addWidget(self.opacity)

        interaction = self._group("交互")
        inter = interaction.layout()
        row = QHBoxLayout()
        row.addWidget(QLabel("气泡显示时长"))
        row.addStretch(1)
        self.bubble_value = QLabel()
        row.addWidget(self.bubble_value)
        inter.addLayout(row)
        self.bubble = QSlider(Qt.Horizontal)
        self.bubble.setRange(60, 160)
        self.bubble.valueChanged.connect(self.bubble_changed)
        inter.addWidget(self.bubble)

        self.speech = QPushButton("对话气泡")
        self.speech.setCheckable(True)
        self.speech.clicked.connect(self.toggle_speech)
        inter.addWidget(self.speech)

        inter.addWidget(QLabel("心情状态胶囊"))
        self.hud_group = QButtonGroup(self)
        self.hud_group.setExclusive(True)
        hud_segmented = QHBoxLayout()
        for idx, (mode, label) in enumerate((("smart", "互动时"), ("always", "始终"), ("off", "关闭"))):
            button = QPushButton(label)
            button.setCheckable(True)
            button.clicked.connect(lambda checked=False, m=mode: self.set_hud_mode(m))
            self.hud_group.addButton(button, idx)
            self.hud_buttons[mode] = button
            hud_segmented.addWidget(button)
        inter.addLayout(hud_segmented)
        hint = QLabel("“互动时”会在点击、喂食、玩耍或状态变化后短暂显示，更适合长期常驻。")
        hint.setObjectName("secondary")
        hint.setWordWrap(True)
        inter.addWidget(hint)

        info = self._group("当前状态")
        self.info = QLabel()
        self.info.setWordWrap(True)
        info.layout().addWidget(self.info)

        root.addWidget(appearance)
        root.addWidget(interaction)
        root.addWidget(info)

        buttons = QHBoxLayout()
        reset = QPushButton("恢复默认")
        reset.setObjectName("secondaryButton")
        reset.clicked.connect(self.reset_defaults)
        done = QPushButton("完成")
        done.setObjectName("primaryButton")
        done.clicked.connect(self.accept)
        buttons.addWidget(reset)
        buttons.addStretch(1)
        buttons.addWidget(done)
        root.addLayout(buttons)
        self.sync_from_pet()

    def _group(self, title):
        frame = QFrame()
        frame.setObjectName("group")
        add_shadow(frame, alpha=14, blur=22, y=5)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)
        label = QLabel(title)
        label.setFont(ui_font(15, QFont.DemiBold))
        layout.addWidget(label)
        return frame

    def set_theme(self, mode):
        self.pet.ui_state["theme_mode"] = mode
        self.pet.apply_ui_state()
        self.sync_from_pet()

    def opacity_changed(self, value):
        self.pet.ui_state["opacity"] = value / 100.0
        self.opacity_value.setText("{}%".format(value))
        self.pet.apply_ui_state()

    def bubble_changed(self, value):
        self.pet.ui_state["bubble_scale"] = value / 100.0
        self.bubble_value.setText("{}%".format(value))
        self.pet.apply_ui_state()

    def toggle_speech(self, checked=False):
        self.pet.ui_state["speech_enabled"] = bool(checked)
        self.pet.apply_ui_state()

    def set_hud_mode(self, mode):
        self.pet.ui_state["hud_mode"] = mode
        self.pet.apply_ui_state()
        self.pet.reveal_hud(4.0)

    def reset_defaults(self):
        self.pet.ui_state.update(DEFAULT_UI)
        self.pet.apply_ui_state()
        self.sync_from_pet()
        self.pet.bubble.show("已恢复默认设置～", 2.0)
        self.pet.reveal_hud(4.0)

    def sync_from_pet(self):
        self.avatar.setPixmap(self.pet.make_avatar_pixmap(84, 98).scaled(
            64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        opacity = int(round(self.pet.ui_state["opacity"] * 100))
        bubble = int(round(self.pet.ui_state["bubble_scale"] * 100))
        self.opacity.blockSignals(True)
        self.opacity.setValue(opacity)
        self.opacity.blockSignals(False)
        self.opacity_value.setText("{}%".format(opacity))
        self.bubble.blockSignals(True)
        self.bubble.setValue(bubble)
        self.bubble.blockSignals(False)
        self.bubble_value.setText("{}%".format(bubble))
        self.speech.blockSignals(True)
        self.speech.setChecked(bool(self.pet.ui_state["speech_enabled"]))
        self.speech.blockSignals(False)
        mode = self.pet.ui_state["theme_mode"]
        for key, button in self.theme_buttons.items():
            button.setChecked(key == mode)
        hud_mode = self.pet.ui_state.get("hud_mode", "smart")
        for key, button in self.hud_buttons.items():
            button.setChecked(key == hud_mode)
        theme_names = {"light": "浅色", "dark": "深色", "system": "跟随系统"}
        hud_names = {"smart": "互动时显示", "always": "始终显示", "off": "关闭"}
        self.info.setText("当前：{} · 主题 {}（生效：{}） · HUD {} · {}".format(
            MODE_LABELS.get(self.pet.character.mode, "陪伴中"), theme_names.get(mode, "跟随系统"),
            self.pet.effective_theme_name(), hud_names.get(hud_mode, "互动时显示"),
            "桌宠已隐藏" if self.pet.pet_hidden else "桌宠显示中"))
        self.apply_theme()

    def apply_theme(self):
        colors = self.pet.current_colors()
        self.setStyleSheet("""
            QDialog {{ background:{}; color:{}; }}
            QFrame#group {{ background:{}; border:1px solid {}; border-radius:16px; }}
            QLabel {{ color:{}; background:transparent; }}
            QLabel#secondary {{ color:{}; }}
            QSlider::groove:horizontal {{ height:4px; background:{}; border-radius:2px; }}
            QSlider::sub-page:horizontal {{ background:{}; border-radius:2px; }}
            QSlider::handle:horizontal {{ width:16px; margin:-6px 0; background:{}; border:1px solid {}; border-radius:8px; }}
            QPushButton {{ background:{}; color:{}; border:1px solid {}; border-radius:10px; padding:8px 14px; }}
            QPushButton:hover {{ background:{}; }}
            QPushButton:checked {{ background:{}; border:1px solid {}; }}
            QPushButton#primaryButton {{ background:{}; color:white; border:1px solid {}; }}
            QPushButton#secondaryButton {{ background:transparent; color:{}; }}
        """.format(
            css(colors["floating"]), css(colors["text"]), css(colors["surface"]), css(colors["border"]),
            css(colors["text"]), css(colors["secondary"]), css(colors["track"]),
            css(colors["accent"]), css(colors["surface_strong"]), css(colors["border"]),
            css(colors["surface_soft"]), css(colors["text"]), css(colors["border"]),
            css(colors["surface_strong"]), css(colors["accent_soft"]), css(colors["accent"]),
            css(colors["accent"]), css(colors["accent"]), css(colors["secondary"])))
