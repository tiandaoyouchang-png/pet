#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 docs/preview.png 预览图（离屏渲染，不弹出窗口）。"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QImage, QPainter
import pixar_pet as pet


def render_character(mode, frames=80):
    c = pet.Character()
    c.enter_mode(mode)
    for _ in range(frames):
        c.update(1 / 30, QPointF(pet.CX, pet.BODY_CY), False)
    img = QImage(pet.W, pet.H, QImage.Format_ARGB32_Premultiplied)
    img.fill(Qt.transparent)
    p = QPainter(img)
    c.draw(p)
    p.end()
    return img


def make_preview():
    from PIL import Image

    os.makedirs("docs", exist_ok=True)
    modes = ["idle", "wave", "dance", "sleep", "stretch", "ball"]
    labels = ["Idle", "Wave", "Dance", "Sleep", "Stretch", "Ball"]
    cell_w, cell_h, cols = 360, 440, 3
    rows = (len(modes) + cols - 1) // cols
    sheet = Image.new("RGBA", (cell_w * cols, cell_h * rows), (245, 240, 232, 255))
    for i, (mode, label) in enumerate(zip(modes, labels)):
        qimg = render_character(mode, frames=180 if mode == "sleep" else 80)
        path = f"/tmp/pet_preview_{mode}.png"
        qimg.save(path)
        cell = Image.open(path).convert("RGBA")
        x, y = (i % cols) * cell_w, (i // cols) * cell_h
        sheet.alpha_composite(cell, (x, y))
        print("rendered", label)
    sheet.save("docs/preview.png")
    print("saved docs/preview.png")


if __name__ == "__main__":
    sys.exit(make_preview())
