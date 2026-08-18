#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render the current UI implementation to PNGs without image generation."""
from pathlib import Path
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
from PySide6.QtWidgets import QApplication

import pixar_pet as core
from momo_app import ApplePetWindow, PreferencesDialog, StatusCard

OUT = Path("artifacts/ui-preview")
OUT.mkdir(parents=True, exist_ok=True)


def grab(widget, filename):
    widget.show()
    app.processEvents()
    pix = widget.grab()
    path = OUT / filename
    pix.save(str(path))
    return pix


app = QApplication([])
app.setApplicationName(core.APP_NAME)
app.setQuitOnLastWindowClosed(False)

pet = ApplePetWindow(app)
pet.timer.stop()
pet.bubble.show("嗨！我是 Momo～", 60.0)
pet.character.enter_mode("idle", 60.0)
pet.needs.update({"mood": 0.82, "hunger": 0.71, "energy": 0.86, "social": 0.77})
pet_pix = grab(pet, "01-pet-window.png")

status = StatusCard(pet)
status.refresh()
status_pix = grab(status, "02-status-card.png")

prefs = PreferencesDialog(pet)
prefs_pix = grab(prefs, "03-preferences.png")

menu = pet._build_menu()
menu_pix = grab(menu, "04-menu.png")

# Compose a neutral contact sheet from the actual grabs.
margin = 36
header = 92
col_gap = 30
row_gap = 30
left_w = max(pet_pix.width(), prefs_pix.width())
right_w = max(status_pix.width(), menu_pix.width())
top_h = max(pet_pix.height(), status_pix.height())
bottom_h = max(prefs_pix.height(), menu_pix.height())
canvas = QPixmap(margin * 2 + left_w + col_gap + right_w,
                 header + margin * 2 + top_h + row_gap + bottom_h)
canvas.fill(QColor(244, 244, 247))

p = QPainter(canvas)
p.setRenderHint(QPainter.Antialiasing)
font = QFont("PingFang SC")
font.setPixelSize(28)
font.setWeight(QFont.DemiBold)
p.setFont(font)
p.setPen(QColor(29, 29, 31))
p.drawText(margin, 48, "Momo 当前代码真实渲染")
font.setPixelSize(14)
font.setWeight(QFont.Normal)
p.setFont(font)
p.setPen(QColor(110, 110, 115))
p.drawText(margin, 74, "ui/apple-polish · Qt widget.grab() · 非 AI 概念图")

y1 = header + margin
x1 = margin
x2 = margin + left_w + col_gap
p.drawPixmap(x1, y1, pet_pix)
p.drawPixmap(x2, y1, status_pix)
y2 = y1 + top_h + row_gap
p.drawPixmap(x1, y2, prefs_pix)
p.drawPixmap(x2, y2, menu_pix)
p.end()

canvas.save(str(OUT / "00-current-state-contact-sheet.png"))
print("Rendered:")
for item in sorted(OUT.glob("*.png")):
    print(item)

status.close()
prefs.close()
menu.close()
pet.close()
app.quit()
