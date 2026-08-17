#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Momo 桌面宠物 —— Pixar 动画风格
一只软乎乎的橘子小怪兽，会自己溜达、打盹、跳舞、发呆、要吃的，
也可以被戳、被摸、被拎起来，会像真的小家伙一样盯着你的鼠标看。

依赖：PySide6
运行：python pixar_pet.py
"""
import ctypes
import json
import math
import os
import random
import sys
from datetime import datetime

from PySide6.QtCore import (
    QEasingCurve, QPoint, QPointF, QPropertyAnimation, QRectF, Qt, QTimer,
)
from PySide6.QtGui import (
    QAction, QColor, QCursor, QFont, QIcon, QLinearGradient,
    QPainter, QPainterPath, QPen, QPixmap, QPolygonF, QRadialGradient,
)
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon, QWidget

# macOS 原生置顶：让 Momo 跨 Space、全屏 App 之上也保持可见
try:
    import objc as _objc
    from AppKit import (
        NSFloatingWindowLevel,
        NSApplicationActivationPolicyAccessory,
        NSWindowCollectionBehaviorCanJoinAllSpaces,
        NSWindowCollectionBehaviorFullScreenAuxiliary,
        NSWindowStyleMaskNonactivatingPanel,
    )
    _HAVE_APPKIT = True
except Exception:
    _HAVE_APPKIT = False

APP_NAME = "Momo 桌宠"
W, H = 360, 440
CX = 180.0          # 角色中心 x
BODY_CY = 248.0     # 身体中心 y（基准）
BASELINE = 380.0    # 脚底在窗口内的 y
FPS = 60
SAVE_PATH = os.path.join(os.path.expanduser("~"), ".momo_pet.json")

LINES = {
    "start": ["嗨！我是 Momo，你的桌面小伙伴～", "我来啦！今天也要一起加油！",
              "你好呀，我会自己玩，也会陪着你～"],
    "idle": ["今天也要可可爱爱～", "嗯…待会儿做点什么呢？", "（小小声哼着歌）",
             "今天的阳光真不错。", "呼——深呼吸一下。", "保持可爱，保持开心！"],
    "wander": ["去那边看看！", "换个地方晒太阳～", "溜达溜达～",
               "巡视一下我的地盘！", "散散步，心情好～"],
    "glance": ["你在干嘛呀？", "我是不是很可爱？", "嘿嘿，被你发现啦。",
               "需要我帮忙吗？", "我一直都在哦。"],
    "stretch": ["伸个懒腰～", "活动活动筋骨！", "啊——舒服多了。", "一二三四，二二三四～"],
    "yawn": ["哈啊～有点困困的。", "打个小哈欠…", "眼睛都要睁不开啦。"],
    "daydream": ["想去看海…", "如果我会飞的话…", "晚饭吃小蛋糕就好了。",
                 "星星什么时候出来呀？", "云朵一定很软吧。"],
    "dance": ["啦啦啦～♪", "今天心情超好！", "来点音乐！", "跟我一起摇摆～", "跳舞使我快乐！"],
    "sleep": ["呼…呼…", "Zzz…", "梦里也在冒险～", "让我再睡五分钟…"],
    "hungry": ["肚子咕咕叫…", "有没有小饼干呀？", "好想吃甜甜圈…",
               "饿得都快没电啦。", "闻到了零食的味道！"],
    "lonely": ["陪我玩一会儿嘛～", "看我！看我！", "别走嘛…", "我都无聊得数自己的睫毛了。"],
    "poke": ["呀！", "嘿嘿，好痒～", "你戳到我啦！", "怎么啦？", "（开心地转了一圈）"],
    "pet": ["好舒服～", "再摸摸嘛～", "最喜欢你啦！", "呼噜呼噜…像小猫一样。", "可以一直这样吗？"],
    "drag": ["哇——飞起来啦！", "小心点呀～", "呜哇哇！", "我在飞！"],
    "drop": ["安全着陆！", "呼，好险。", "刚刚好刺激！"],
    "eat": ["好吃！", "啊呜啊呜～", "甜滋滋的！", "再来一块嘛～", "幸福！"],
    "wave": ["你好呀！", "我在这里～", "嗨嗨！"],
    "ball": ["球球别跑！", "接住！", "看我无敌弹跳！"],
    "wake": ["我醒啦！", "早上好呀…现在几点啦？", "做了一个好梦！"],
    "tickle": ["哈哈哈别挠啦！", "好痒好痒！", "咯咯咯～"],
    "highfive": ["耶！Give me five！", "配合完美！", "嘿嘿！"],
}


def say(pool):
    return random.choice(LINES[pool])


def clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))


def lerp(a, b, t):
    return a + (b - a) * t


def smoothstep(t):
    t = clamp(t)
    return t * t * (3.0 - 2.0 * t)


def ease_out_elastic(t):
    t = clamp(t)
    if t <= 0.0:
        return 0.0
    if t >= 1.0:
        return 1.0
    c4 = (2.0 * math.pi) / 3.0
    return math.pow(2.0, -10.0 * t) * math.sin((t * 10.0 - 0.75) * c4) + 1.0


class Character:
    """角色的脸、肢体、姿态和 Pixar 式渲染。"""

    def __init__(self):
        self.t = 0.0
        self.mode = "idle"
        self.mode_elapsed = 0.0
        self.mode_duration = 5.0
        self.next_blink = random.uniform(1.2, 3.5)
        self.blink_t = -1.0
        self.facing = 1.0
        self.look_x = 0.0
        self.look_y = 0.0
        self.look_smooth = QPointF(0.0, 0.0)
        self.held = False
        self.petting = False
        self.hover_elapsed = 0.0
        self.walk_phase = 0.0
        self.squash_x = 1.0
        self.squash_y = 1.0
        self.jump_y = 0.0
        self.land_t = -1.0
        self.eye_open = 1.0
        self.mouth_anim = 0.0
        self.brow_raise = 0.0
        self.cookie = None
        self.ball = None
        self.eat_t = -1.0

    def enter_mode(self, mode, duration=None):
        self.mode = mode
        self.mode_elapsed = 0.0
        self.mode_duration = duration if duration is not None else self.default_duration(mode)
        if mode == "land":
            self.land_t = 0.0
        if mode == "eat":
            self.eat_t = 0.0
            self.cookie = {"x": -70.0, "y": 10.0, "r": 17.0}
        if mode == "ball":
            self.spawn_ball()
        return self.mode_duration

    @staticmethod
    def default_duration(mode):
        return {
            "idle": random.uniform(3.5, 7.5),
            "wander": 0.0,
            "glance": random.uniform(2.4, 4.5),
            "stretch": random.uniform(2.8, 4.0),
            "yawn": random.uniform(2.6, 3.6),
            "daydream": random.uniform(5.0, 9.0),
            "dance": random.uniform(5.0, 8.0),
            "sleep": random.uniform(25.0, 60.0),
            "held": 999.0,
            "pet": 999.0,
            "eat": random.uniform(3.6, 4.6),
            "ball": random.uniform(8.0, 12.0),
            "wave": random.uniform(2.6, 3.4),
            "land": random.uniform(0.8, 1.2),
            "hungry": random.uniform(4.0, 5.5),
        }.get(mode, 4.0)

    def spawn_ball(self):
        self.ball = {
            "x": random.uniform(80, W - 80), "y": 180.0,
            "vx": random.uniform(90, 150) * random.choice([-1, 1]),
            "vy": random.uniform(-160, -60),
        }

    def update(self, dt, mouse_local, mouse_inside):
        self.t += dt
        self.mode_elapsed += dt

        # 眨眼
        self.next_blink -= dt
        if self.next_blink <= 0.0:
            self.blink_t = 0.0
            self.next_blink = random.uniform(1.8, 5.0)
        if self.blink_t >= 0.0:
            self.blink_t += dt
            if self.blink_t > 0.28:
                self.blink_t = -1.0
        if self.mode == "sleep":
            self.eye_open = clamp(0.06 + 0.04 * math.sin(self.t * 2.2))
        elif self.blink_t >= 0.0:
            p = self.blink_t / 0.28
            if p < 0.35:
                self.eye_open = 1.0 - smoothstep(p / 0.35)
            elif p < 0.7:
                self.eye_open = 0.0
            else:
                self.eye_open = smoothstep((p - 0.7) / 0.3)
        else:
            self.eye_open = lerp(self.eye_open, 1.0, min(1.0, dt * 18.0))

        # 视线：平时东张西望，鼠标靠近时看鼠标
        target = QPointF(math.sin(self.t * 0.7) * 0.35, math.sin(self.t * 1.3 + 1.0) * 0.25)
        if mouse_inside and self.mode != "sleep":
            rel_x = clamp((mouse_local.x() - CX) / 150.0, -1.0, 1.0)
            rel_y = clamp((mouse_local.y() - 215.0) / 140.0, -1.0, 1.0)
            target = QPointF(rel_x * 0.85, rel_y * 0.7)
        self.look_smooth += (target - self.look_smooth) * min(1.0, dt * 9.0)
        self.look_x = self.look_smooth.x()
        self.look_y = self.look_smooth.y()

        # 眉毛
        if self.mode == "hungry":
            target_brow = 0.85
        elif self.mode in ("sleep", "yawn"):
            target_brow = 0.25
        elif self.mode in ("dance", "wave", "pet", "eat"):
            target_brow = -0.5
        else:
            target_brow = 0.0
        self.brow_raise = lerp(self.brow_raise, target_brow, min(1.0, dt * 5.0))

        # 走路 / 跳舞相位
        if self.mode == "wander":
            self.walk_phase += dt * 11.0
            self.mouth_anim = 0.6 + 0.4 * math.sin(self.walk_phase * 2.0)
        elif self.mode == "dance":
            self.walk_phase += dt * 7.0
            self.mouth_anim = 0.5 + 0.5 * math.sin(self.walk_phase * 3.0)
        else:
            self.mouth_anim = lerp(self.mouth_anim, 0.0, min(1.0, dt * 6.0))

        # 挤压与拉伸
        if self.land_t >= 0.0:
            self.land_t += dt
            pr = self.land_t / 0.55
            if pr < 1.0:
                self.squash_y = lerp(0.62, 1.0, ease_out_elastic(pr))
                self.squash_x = lerp(1.42, 1.0, ease_out_elastic(pr))
            else:
                self.squash_x = self.squash_y = 1.0
                if self.land_t > 1.3:
                    self.land_t = -1.0
        else:
            breath = 0.018 * math.sin(self.t * math.pi * 2.0 * 0.45)
            stretch = 0.0
            if self.mode == "stretch":
                stretch = 0.085 * math.sin(math.pi * clamp(self.mode_elapsed / 1.4)) * \
                          math.sin(math.pi * clamp(self.mode_elapsed / self.mode_duration))
            bob = 0.0
            if self.mode == "wander":
                bob = abs(math.sin(self.walk_phase)) * 0.04
            elif self.mode == "dance":
                bob = abs(math.sin(self.walk_phase * 2.0)) * 0.06
            elif self.mode == "ball":
                bob = abs(math.sin(self.t * 9.0)) * 0.10
            elif self.mode == "eat":
                bob = math.sin(max(0.0, self.eat_t) * 10.0) * 0.02
            self.squash_y = 1.0 + breath + bob + stretch * 0.55
            self.squash_x = 1.0 - breath * 0.75 - bob * 0.7 - stretch * 0.3

        # 被拎起来：轻微摆动
        if self.mode == "held":
            sway = math.sin(self.t * 4.2) * 0.02
            self.squash_x = 1.05 + sway
            self.squash_y = 0.94
            self.eye_open = lerp(self.eye_open, 0.72, min(1.0, dt * 6.0))

        # 吃东西
        if self.cookie is not None and self.eat_t >= 0.0:
            self.eat_t += dt
            p = clamp(self.eat_t / 1.4)
            self.cookie["x"] = lerp(-70.0, 55.0, p)
            self.cookie["y"] = lerp(10.0, -24.0, p) - 8.0 * math.sin(p * math.pi)
        if self.mode == "eat" and self.mode_elapsed > self.mode_duration:
            self.cookie = None
            self.eat_t = -1.0

        # 小球物理
        if self.ball is not None:
            b = self.ball
            b["x"] += b["vx"] * dt
            b["y"] += b["vy"] * dt
            b["vy"] += 720.0 * dt
            if b["x"] < 34 or b["x"] > W - 34:
                b["x"] = clamp(b["x"], 34, W - 34)
                b["vx"] *= -0.85
            if b["y"] > 352:
                b["y"] = 352
                b["vy"] *= -0.62
                b["vx"] *= 0.92
                if abs(b["vy"]) < 40:
                    b["vy"] = -random.uniform(150.0, 260.0)
            if b["y"] < 70:
                b["y"] = 70
                b["vy"] *= -0.7
        if self.mode == "ball" and self.mode_elapsed > self.mode_duration:
            self.ball = None

    # ---------------- 绘制入口 ----------------
    def draw(self, p: QPainter):
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)

        if self.ball is not None:
            self.draw_ball(p)

        # 地面阴影：挤压时变宽，跳起时变淡
        shadow_w = 92.0 * (1.7 - self.squash_x * 0.7)
        shadow_y = BASELINE + 6
        for mult, alpha in [(1.0, 24), (0.72, 30), (0.46, 38)]:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(40, 22, 8, alpha))
            p.drawEllipse(QPointF(CX, shadow_y), shadow_w * mult, 13.0 * mult)

        p.save()
        p.translate(CX, BODY_CY + self.jump_y)
        p.scale(self.squash_x, self.squash_y)
        p.translate(-CX, -BODY_CY)

        back_pose = self.arm_pose(side=-1, back=True)
        self.draw_arm(p, back_pose, back=True)
        self.draw_body(p)
        front_pose = self.arm_pose(side=1, back=False)
        self.draw_arm(p, front_pose, back=False)
        self.draw_face(p)
        self.draw_sprout(p)
        p.restore()

        if self.cookie is not None and self.eat_t >= 0.0:
            self.draw_cookie(p)

    # ---------------- 手臂 ----------------
    def arm_pose(self, side, back):
        s = side * self.facing
        cx = CX + s * 74.0
        sy = BODY_CY - 18.0
        w1, w2 = 26.0, 16.0
        if self.mode == "held":
            return (QPointF(cx, sy), QPointF(CX + s * 46.0, BODY_CY - 142.0), w1, w2)
        if self.mode == "stretch":
            ph = math.sin(math.pi * clamp(self.mode_elapsed / self.mode_duration))
            return (QPointF(cx, sy), QPointF(CX + s * 58.0, BODY_CY - 150.0 - 8 * ph), w1, w2)
        if self.mode == "wave" and not back:
            ph = math.sin(math.pi * clamp(self.mode_elapsed / self.mode_duration))
            wig = math.sin(self.t * 14.0) * 7.0
            return (QPointF(cx, sy), QPointF(CX + s * 88.0, BODY_CY - 102.0 + wig * ph), w1, w2)
        if self.mode == "dance":
            ph = math.sin(self.walk_phase + (0.0 if back else math.pi))
            return (QPointF(cx, sy),
                    QPointF(CX + s * 80.0, BODY_CY - 28.0 - 78.0 * max(0.0, ph)), w1, w2)
        if self.mode == "sleep":
            return (QPointF(cx, sy), QPointF(CX + s * 58.0, BODY_CY + 18.0), w1, w2)
        if self.mode == "eat" and side == 1 and not back:
            return (QPointF(cx, sy), QPointF(CX + 34.0 * self.facing, BODY_CY + 24.0), w1, w2)
        if self.mode == "scratch" and side == 1 and not back:
            return (QPointF(cx, sy), QPointF(CX + 28.0 * self.facing, BODY_CY - 102.0), w1, w2)
        swing = 0.0
        if self.mode == "wander":
            swing = math.sin(self.walk_phase + (0.0 if back else math.pi)) * 0.35
        elif self.mode == "ball":
            swing = math.sin(self.t * 9.0) * 0.5
        elif self.mode == "pet":
            swing = 0.16
        hx = CX + s * 80.0 + swing * 18.0 * s
        hy = BODY_CY + 28.0 + math.sin(self.t * 1.7 + side) * 3.0
        if self.mode == "yawn":
            hx = CX + s * 72.0
            hy = BODY_CY - 6.0
        return (QPointF(cx, sy), QPointF(hx, hy), w1, w2)

    def _limb_path(self, a, b, w1, w2):
        dx, dy = b.x() - a.x(), b.y() - a.y()
        length = max(1.0, math.hypot(dx, dy))
        nx, ny = -dy / length, dx / length
        bulge = 3.0 + (w1 + w2) * 0.18
        mid = QPointF((a.x() + b.x()) * 0.5 + nx * bulge,
                      (a.y() + b.y()) * 0.5 + ny * bulge)
        path = QPainterPath()
        path.moveTo(a.x() + nx * w1 * 0.5, a.y() + ny * w1 * 0.5)
        path.quadTo(mid.x() + nx * w2 * 0.1, mid.y() + ny * w2 * 0.1,
                    b.x() + nx * w2 * 0.5, b.y() + ny * w2 * 0.5)
        path.lineTo(b.x() - nx * w2 * 0.5, b.y() - ny * w2 * 0.5)
        path.quadTo(mid.x() - nx * w2 * 0.1, mid.y() - ny * w2 * 0.1,
                    a.x() - nx * w1 * 0.5, a.y() - ny * w1 * 0.5)
        path.closeSubpath()
        return path

    def draw_arm(self, p, pose, back=False):
        a, b, w1, w2 = pose
        grad = QLinearGradient(a, b)
        if back:
            grad.setColorAt(0.0, QColor(244, 154, 56))
            grad.setColorAt(1.0, QColor(222, 116, 32))
            edge = QColor(178, 86, 16, 210)
            hand_col = QColor(238, 146, 48)
        else:
            grad.setColorAt(0.0, QColor(255, 184, 76))
            grad.setColorAt(0.55, QColor(255, 151, 50))
            grad.setColorAt(1.0, QColor(236, 116, 30))
            edge = QColor(176, 82, 14, 235)
            hand_col = QColor(255, 176, 78)
        path = self._limb_path(a, b, w1, w2)
        p.setPen(QPen(edge, 2.4))
        p.setBrush(grad)
        p.drawPath(path)

        # 手套式圆手 + 大拇指
        ang = math.degrees(math.atan2(b.y() - a.y(), b.x() - a.x()))
        p.save()
        p.translate(b)
        p.rotate(ang)
        p.setPen(QPen(edge, 2.2))
        p.setBrush(hand_col)
        p.drawEllipse(QPointF(0, 0), w2 * 0.82, w2 * 0.72)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 224, 166, 110))
        p.drawEllipse(QPointF(-w2 * 0.28, -w2 * 0.30), w2 * 0.42, w2 * 0.30)
        p.restore()

    # ---------------- 身体 ----------------
    def _body_path(self):
        path = QPainterPath()
        path.moveTo(CX, 120)
        path.cubicTo(CX - 58, 114, CX - 98, 142, CX - 106, 194)
        path.cubicTo(CX - 114, 254, CX - 94, 328, CX - 64, 364)
        path.cubicTo(CX - 40, 392, CX - 18, 379, CX, 379)
        path.cubicTo(CX + 18, 379, CX + 40, 392, CX + 64, 364)
        path.cubicTo(CX + 94, 328, CX + 114, 254, CX + 106, 194)
        path.cubicTo(CX + 98, 142, CX + 58, 114, CX, 120)
        path.closeSubpath()
        return path

    def draw_body(self, p):
        body_path = self._body_path()
        rim = QColor(168, 76, 14)

        # 柔和的深色包边（多层模拟软边）
        for width, alpha in [(17.0, 16), (11.0, 26), (6.5, 44)]:
            p.setPen(QPen(QColor(rim.red(), rim.green(), rim.blue(), alpha),
                          width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.setBrush(Qt.NoBrush)
            p.drawPath(body_path)

        # 主体：顶部受光的暖橙渐变
        body_grad = QRadialGradient(QPointF(CX - 38, 154), 250)
        body_grad.setColorAt(0.0, QColor(255, 244, 198))
        body_grad.setColorAt(0.28, QColor(255, 214, 124))
        body_grad.setColorAt(0.62, QColor(255, 162, 60))
        body_grad.setColorAt(0.85, QColor(248, 122, 32))
        body_grad.setColorAt(1.0, QColor(225, 98, 24))
        p.setPen(Qt.NoPen)
        p.setBrush(body_grad)
        p.drawPath(body_path)

        p.save()
        p.setClipPath(body_path)

        # 左上大面积柔光
        key_light = QRadialGradient(QPointF(CX - 62, 162), 120)
        key_light.setColorAt(0.0, QColor(255, 252, 224, 190))
        key_light.setColorAt(0.55, QColor(255, 246, 200, 70))
        key_light.setColorAt(1.0, QColor(255, 246, 200, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(key_light)
        p.drawEllipse(QPointF(CX - 52, 178), 92, 72)

        # 右下环境光反射（让球体有 3D 体积感）
        bounce = QRadialGradient(QPointF(CX + 66, 352), 105)
        bounce.setColorAt(0.0, QColor(255, 120, 74, 150))
        bounce.setColorAt(1.0, QColor(255, 120, 74, 0))
        p.setBrush(bounce)
        p.drawEllipse(QPointF(CX + 62, 340), 78, 52)

        # 底部微弱反光
        bottom_light = QLinearGradient(QPointF(CX, 330), QPointF(CX, 382))
        bottom_light.setColorAt(0.0, QColor(255, 214, 150, 0))
        bottom_light.setColorAt(1.0, QColor(255, 226, 168, 120))
        p.setBrush(bottom_light)
        p.drawEllipse(QPointF(CX, 366), 82, 22)

        # 肚皮：奶油色，带自己的渐变与高光
        belly_path = QPainterPath()
        belly_path.addEllipse(QPointF(CX, 304), 64, 76)
        belly_grad = QRadialGradient(QPointF(CX, 280), 110)
        belly_grad.setColorAt(0.0, QColor(255, 251, 230, 245))
        belly_grad.setColorAt(0.6, QColor(255, 238, 196, 235))
        belly_grad.setColorAt(1.0, QColor(255, 216, 150, 160))
        p.setBrush(belly_grad)
        p.setPen(QPen(QColor(214, 132, 52, 90), 2.0))
        p.drawPath(belly_path)
        belly_shine = QRadialGradient(QPointF(CX - 14, 272), 44)
        belly_shine.setColorAt(0.0, QColor(255, 255, 246, 180))
        belly_shine.setColorAt(1.0, QColor(255, 255, 246, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(belly_shine)
        p.drawEllipse(QPointF(CX - 14, 278), 36, 26)

        # 两个高光小点
        p.setBrush(QColor(255, 255, 240, 190))
        p.drawEllipse(QPointF(CX - 56, 168), 7, 5)
        p.drawEllipse(QPointF(CX - 80, 214), 4, 3)

        p.restore()

        # 最后描一道很细的外轮廓，提高在浅色桌面上的可读性
        p.setPen(QPen(QColor(150, 70, 14, 80), 1.6))
        p.setBrush(Qt.NoBrush)
        p.drawPath(body_path)

        # 脚（鞋型，两只小脚前后错落）
        step = 0.0
        if self.mode == "wander":
            step = math.sin(self.walk_phase) * 15.0
        elif self.mode == "dance":
            step = math.sin(self.walk_phase * 2.0) * 8.0
        elif self.mode == "ball":
            step = math.sin(self.t * 9.0) * 10.0
        for side in (-1, 1):
            fx = CX + side * 52.0 + step * side * 0.55
            fy = BODY_CY + 122.0 - abs(step) * 0.35
            foot = QRadialGradient(QPointF(fx - 6, fy - 5), 38)
            foot.setColorAt(0.0, QColor(255, 190, 92))
            foot.setColorAt(1.0, QColor(236, 118, 34))
            p.setPen(QPen(QColor(172, 82, 16, 220), 2.4))
            p.setBrush(foot)
            p.drawEllipse(QPointF(fx, fy), 29, 16.5)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 224, 164, 130))
            p.drawEllipse(QPointF(fx - 8, fy - 5), 10, 5)

    # ---------------- 脸 ----------------
    @staticmethod
    def _eye_path(ex, ey, rx, ry):
        path = QPainterPath()
        path.moveTo(ex - rx, ey)
        path.cubicTo(ex - rx * 0.9, ey - ry, ex + rx * 0.9, ey - ry, ex + rx, ey)
        path.cubicTo(ex + rx * 0.9, ey + ry, ex - rx * 0.9, ey + ry, ex - rx, ey)
        path.closeSubpath()
        return path

    def _draw_eyelid(self, p, ex, ey, rx, ry, cover):
        """cover=0 睁眼，cover=1 闭眼。用皮肤色眼睑从上方盖住眼球。"""
        lid_y = lerp(ey - ry * 0.58, ey + ry * 1.02, cover)
        top = ey - ry - 9
        path = QPainterPath()
        path.moveTo(ex - rx - 5, top)
        path.lineTo(ex + rx + 5, top)
        path.lineTo(ex + rx + 5, lid_y)
        path.quadTo(ex, lid_y + 7, ex - rx - 5, lid_y)
        path.closeSubpath()
        lid_grad = QLinearGradient(ex, top, ex, ey + ry)
        lid_grad.setColorAt(0.0, QColor(255, 206, 108))
        lid_grad.setColorAt(1.0, QColor(247, 134, 42))
        p.setPen(Qt.NoPen)
        p.setBrush(lid_grad)
        p.drawPath(path)
        edge = QPainterPath()
        edge.moveTo(ex - rx - 5, lid_y)
        edge.quadTo(ex, lid_y + 7, ex + rx + 5, lid_y)
        p.setPen(QPen(QColor(160, 74, 14, 210), 2.6,
                      Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        p.drawPath(edge)
        return lid_y

    def _draw_brow(self, p, bx, brow_y, tilt):
        path = QPainterPath()
        path.moveTo(bx - 26, brow_y + 3)
        path.cubicTo(bx - 12, brow_y - 9, bx + 10, brow_y - 11,
                     bx + 28, brow_y - 9 + tilt)
        path.cubicTo(bx + 10, brow_y - 3 + tilt, bx - 12, brow_y + 6,
                     bx - 26, brow_y + 8)
        path.closeSubpath()
        p.setPen(QPen(QColor(88, 44, 15, 230), 1.6,
                      Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(QColor(106, 55, 20))
        p.drawPath(path)
        # 眉毛顶部一点高光
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 190, 110, 90))
        p.drawEllipse(QPointF(bx + 8, brow_y - 10 + tilt * 0.5), 9, 3.4)

    def draw_face(self, p):
        s = self.facing
        eye_open = clamp(self.eye_open, 0.0, 1.0)
        cover = 1.0 - eye_open
        eye_y = BODY_CY - 30.0
        eye_rx, eye_ry = 32.0, 37.0
        face_shadow = QColor(255, 235, 214, 60)
        iris_col = QColor(96, 57, 30)
        pupil_col = QColor(16, 9, 6)

        for side in (-1, 1):
            ex = CX + s * side * 40.0
            # 眼白
            eye_path = self._eye_path(ex, eye_y, eye_rx, eye_ry)
            white_grad = QLinearGradient(ex, eye_y - eye_ry, ex, eye_y + eye_ry)
            white_grad.setColorAt(0.0, QColor(255, 255, 252))
            white_grad.setColorAt(0.75, QColor(255, 251, 244))
            white_grad.setColorAt(1.0, QColor(248, 240, 232))
            p.setPen(QPen(QColor(112, 55, 18, 170), 2.2))
            p.setBrush(white_grad)
            p.drawPath(eye_path)

            p.save()
            p.setClipPath(eye_path)
            p.setPen(Qt.NoPen)
            p.setBrush(face_shadow)
            p.drawEllipse(QPointF(ex, eye_y + eye_ry * 0.72),
                          eye_rx * 0.9, eye_ry * 0.32)
            p.setBrush(QColor(140, 80, 40, 35))
            p.drawEllipse(QPointF(ex, eye_y - eye_ry * 0.72),
                          eye_rx * 0.92, eye_ry * 0.28)

            # 虹膜：大而亮，带一圈深色边缘
            ix = ex + self.look_x * 10.0 * s
            iy = eye_y + self.look_y * 7.5
            iris = QRadialGradient(QPointF(ix - 2, iy - 5), 26)
            iris.setColorAt(0.0, QColor(151, 101, 57))
            iris.setColorAt(0.5, QColor(98, 60, 32))
            iris.setColorAt(0.85, QColor(64, 37, 21))
            iris.setColorAt(1.0, QColor(46, 26, 15))
            p.setPen(QPen(QColor(38, 20, 11, 235), 2.2))
            p.setBrush(iris)
            p.drawEllipse(QPointF(ix, iy), 15.5, 18.5)
            # 瞳孔
            p.setPen(Qt.NoPen)
            p.setBrush(pupil_col)
            p.drawEllipse(QPointF(ix + 2.0, iy + 1.5), 8.4, 9.8)
            # 高光：一大一小，错开方向才有玻璃感
            p.setBrush(QColor(255, 255, 255, 245))
            p.drawEllipse(QPointF(ix - 5.0, iy - 6.5), 5.2, 5.8)
            p.setBrush(QColor(255, 255, 255, 190))
            p.drawEllipse(QPointF(ix + 6.0, iy + 6.0), 2.8, 3.2)
            p.setBrush(QColor(255, 240, 210, 90))
            p.drawEllipse(QPointF(ix - 7.5, iy + 8.0), 4.0, 2.4)
            p.restore()

            # 眼睑：盖在眼球上方，Pixar 角色最重要的“眼神”
            lid_y = self._draw_eyelid(p, ex, eye_y, eye_rx, eye_ry, cover)
            if eye_open < 0.3:
                p.setPen(QPen(QColor(104, 50, 18, 225), 3.4,
                              Qt.SolidLine, Qt.RoundCap))
                p.setBrush(Qt.NoBrush)
                p.drawArc(QRectF(ex - eye_rx * 0.82, lid_y - 3,
                                 eye_rx * 1.64, 8), 180 * 16, 180 * 16)

            # 双眼皮褶皱
            if eye_open > 0.35:
                crease = lid_y - 11.0
                p.setPen(QPen(QColor(170, 82, 24, 95), 2.2))
                p.setBrush(Qt.NoBrush)
                p.drawArc(QRectF(ex - eye_rx * 0.8, crease - 4,
                                 eye_rx * 1.6, 8), 195 * 16, 150 * 16)

        # 眉毛
        brow_tilt = 5.0 + self.brow_raise * 15.0
        brow_y = eye_y - 55.0 + self.brow_raise * 11.0
        for side in (-1, 1):
            bx = CX + s * side * 40.0
            tilt = brow_tilt * side * s
            self._draw_brow(p, bx, brow_y, tilt)

        # 腮红：两层，更透亮
        for side in (-1, 1):
            rx = CX + s * side * 68.0
            ry = BODY_CY + 8.0
            blush = QRadialGradient(QPointF(rx, ry), 30)
            blush.setColorAt(0.0, QColor(255, 116, 100, 150))
            blush.setColorAt(0.55, QColor(255, 126, 104, 80))
            blush.setColorAt(1.0, QColor(255, 126, 104, 0))
            p.setPen(Qt.NoPen)
            p.setBrush(blush)
            p.drawEllipse(QPointF(rx, ry), 25, 15)
            p.setBrush(QColor(255, 255, 255, 70))
            p.drawEllipse(QPointF(rx - 7, ry - 5), 8, 4)

        self.draw_mouth(p, s)

    def draw_mouth(self, p, s):
        mx = CX + s * 7.0
        my = BODY_CY + 46.0
        p.setBrush(Qt.NoBrush)
        mode = self.mode
        if mode == "sleep":
            path = QPainterPath(QPointF(mx - 9, my + 2))
            path.quadTo(QPointF(mx, my + 8), QPointF(mx + 9, my + 2))
            p.setPen(QPen(QColor(116, 50, 20), 3.0, Qt.SolidLine, Qt.RoundCap))
            p.drawPath(path)
            return
        if mode == "held":
            self._open_mouth(p, mx, my, 8.0, 12.0)
            return
        if mode == "yawn":
            self._open_mouth(p, mx, my, 17.0,
                             22.0 + 6 * math.sin(self.mode_elapsed * 4.0))
            return
        if mode == "eat":
            open_amt = 0.55 + 0.45 * abs(math.sin(self.eat_t * 10.0)) if self.eat_t >= 0 else 0.8
            self._open_mouth(p, mx, my, 11.5, 17.0 * open_amt)
            return
        if mode == "hungry":
            path = QPainterPath(QPointF(mx - 16, my + 4))
            path.quadTo(QPointF(mx, my - 8), QPointF(mx + 16, my + 4))
            p.setPen(QPen(QColor(116, 50, 20), 3.2, Qt.SolidLine, Qt.RoundCap))
            p.drawPath(path)
            return
        if mode in ("dance", "wave"):
            self._open_mouth(p, mx, my, 13.0, 16.0 + self.mouth_anim * 6.0)
            return
        if mode == "ball":
            self._open_mouth(p, mx, my, 10.0, 12.0)
            return

        # 微笑：嘴唇厚一点，再加下唇高光
        smile = QPainterPath(QPointF(mx - 21, my - 1))
        smile.cubicTo(QPointF(mx - 9, my + 11), QPointF(mx + 9, my + 11),
                      QPointF(mx + 21, my - 1))
        p.setPen(QPen(QColor(112, 46, 18), 3.4, Qt.SolidLine, Qt.RoundCap))
        p.drawPath(smile)
        p.setPen(QPen(QColor(255, 206, 150, 110), 2.2))
        p.drawArc(QRectF(mx - 12, my + 2, 24, 10), 200 * 16, 140 * 16)

    def _open_mouth(self, p, mx, my, rx, ry):
        ry = max(ry, 4.0)
        # 口腔
        cavity = QPainterPath()
        cavity.moveTo(mx - rx, my + 2)
        cavity.quadTo(mx, my - ry, mx + rx, my + 2)
        cavity.quadTo(mx + rx * 0.8, my + 2 + ry * 1.35,
                      mx, my + 2 + ry * 1.55)
        cavity.quadTo(mx - rx * 0.8, my + 2 + ry * 1.35,
                      mx - rx, my + 2)
        cavity.closeSubpath()
        mouth_grad = QLinearGradient(mx, my - ry, mx, my + ry * 1.6)
        mouth_grad.setColorAt(0.0, QColor(105, 38, 20))
        mouth_grad.setColorAt(1.0, QColor(68, 22, 14))
        p.setPen(QPen(QColor(88, 36, 18, 235), 2.6,
                      Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(mouth_grad)
        p.drawPath(cavity)
        # 舌头
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 128, 116))
        p.drawEllipse(QPointF(mx, my + 2 + ry * 0.95), rx * 0.66, ry * 0.52)
        p.setBrush(QColor(255, 164, 150, 120))
        p.drawEllipse(QPointF(mx - rx * 0.16, my + 2 + ry * 0.80), rx * 0.28, ry * 0.22)
        # 牙齿：大笑时露一点，更像皮克斯小孩
        if ry >= 9.0:
            tooth_w = max(3.5, rx * 0.22)
            tooth_h = max(3.5, ry * 0.26)
            p.setPen(QPen(QColor(210, 205, 196, 160), 1.2))
            p.setBrush(QColor(255, 255, 250))
            p.drawRoundedRect(QRectF(mx - tooth_w - 1.0, my - ry * 0.55,
                                     tooth_w, tooth_h), 2, 2)
            p.drawRoundedRect(QRectF(mx + 1.0, my - ry * 0.55,
                                     tooth_w, tooth_h), 2, 2)

    # ---------------- 头顶小芽 ----------------
    def draw_sprout(self, p):
        bx = CX + self.facing * 10.0
        by = BODY_CY - 118.0
        sway = math.sin(self.t * 1.7) * 4.0
        tip = QPointF(bx + sway, by - 30)

        stem = QPainterPath()
        stem.moveTo(bx - 3, by + 16)
        stem.cubicTo(bx - 6, by - 2, bx + 2 + sway * 0.5, by - 18,
                     tip.x(), tip.y() + 4)
        stem.cubicTo(bx + 3 + sway * 0.5, by - 16, bx + 6, by + 2,
                     bx + 3, by + 16)
        stem.closeSubpath()
        stem_grad = QLinearGradient(bx, by + 16, tip.x(), tip.y())
        stem_grad.setColorAt(0.0, QColor(86, 136, 50))
        stem_grad.setColorAt(1.0, QColor(124, 184, 74))
        p.setPen(QPen(QColor(58, 96, 32), 2.0))
        p.setBrush(stem_grad)
        p.drawPath(stem)

        leaf = QPainterPath()
        leaf.moveTo(tip.x(), tip.y())
        leaf.cubicTo(tip.x() + 14, tip.y() - 18, tip.x() + 30, tip.y() - 8,
                     tip.x() + 26, tip.y() + 8)
        leaf.cubicTo(tip.x() + 17, tip.y() + 2, tip.x() + 8, tip.y() + 4,
                     tip.x(), tip.y())
        leaf.closeSubpath()
        leaf_grad = QLinearGradient(tip.x(), tip.y() - 12, tip.x() + 28, tip.y() + 8)
        leaf_grad.setColorAt(0.0, QColor(178, 222, 108))
        leaf_grad.setColorAt(0.55, QColor(118, 184, 70))
        leaf_grad.setColorAt(1.0, QColor(84, 142, 48))
        p.setPen(QPen(QColor(54, 94, 30), 2.2))
        p.setBrush(leaf_grad)
        p.drawPath(leaf)
        p.setPen(QPen(QColor(226, 240, 170, 140), 1.8))
        p.drawLine(QPointF(tip.x() + 4, tip.y() - 4), QPointF(tip.x() + 19, tip.y() - 6))
    # ---------------- 小道具 ----------------
    def draw_cookie(self, p):
        c = self.cookie
        x = CX + c["x"] * self.facing
        y = BODY_CY + c["y"]
        r = c["r"]
        p.setPen(QPen(QColor(132, 76, 30), 2.5))
        p.setBrush(QColor(224, 166, 92))
        p.drawEllipse(QPointF(x, y), r, r)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(104, 60, 26))
        for dx, dy in [(-6, -5), (4, -7), (0, 3), (8, 4), (-8, 6)]:
            p.drawEllipse(QPointF(x + dx, y + dy), 2.6, 2.6)

    def draw_ball(self, p):
        b = self.ball
        x, y = b["x"], b["y"]
        grad = QRadialGradient(QPointF(x - 8, y - 10), 40)
        grad.setColorAt(0.0, QColor(255, 255, 240))
        grad.setColorAt(0.35, QColor(120, 200, 230))
        grad.setColorAt(1.0, QColor(50, 125, 175))
        p.setPen(QPen(QColor(32, 90, 130), 2.6))
        p.setBrush(grad)
        p.drawEllipse(QPointF(x, y), 23, 23)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 200))
        p.drawEllipse(QPointF(x - 8, y - 9), 6.5, 6.5)
        star = QPainterPath()
        for i in range(10):
            ang = -math.pi / 2 + i * math.pi / 5
            rr = 10 if i % 2 == 0 else 4.6
            px = x + 9 + rr * math.cos(ang)
            py = y - 4 + rr * math.sin(ang)
            if i == 0:
                star.moveTo(px, py)
            else:
                star.lineTo(px, py)
        star.closeSubpath()
        p.setPen(QPen(QColor(200, 130, 40), 2.0))
        p.setBrush(QColor(255, 190, 70))
        p.drawPath(star)

# ---------------------------------------------------------------- 气泡
class SpeechBubble:
    def __init__(self):
        self.text = ""
        self.t = -1.0
        self.duration = 3.2

    def show(self, text, duration=3.2):
        self.text = text
        self.duration = duration
        self.t = 0.0

    def update(self, dt):
        if self.t >= 0.0:
            self.t += dt
            if self.t > self.duration:
                self.t = -1.0

    def draw(self, p: QPainter):
        if self.t < 0.0 or not self.text:
            return
        appear = smoothstep(self.t / 0.18)
        fade = 1.0 if self.t < self.duration - 0.4 else smoothstep((self.duration - self.t) / 0.4)
        alpha = appear * fade

        font = QFont("PingFang SC")
        font.setPixelSize(19)
        font.setBold(True)
        p.setFont(font)
        fm = p.fontMetrics()
        tw = fm.horizontalAdvance(self.text)
        pad_x, pad_y = 18, 12
        bw, bh = tw + pad_x * 2, 32
        bx = clamp(CX - bw / 2, 10, W - bw - 10)
        by = 14.0
        tail = QPolygonF([
            QPointF(CX - 10, by + bh - 1), QPointF(CX + 10, by + bh - 1),
            QPointF(CX, by + bh + 14),
        ])
        p.save()
        p.setOpacity(alpha)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(50, 30, 15, 36))
        p.drawRoundedRect(QRectF(bx + 3, by + 4, bw, bh), 15, 15)
        p.setBrush(QColor(255, 253, 245))
        p.drawRoundedRect(QRectF(bx, by, bw, bh), 15, 15)
        p.drawPolygon(tail)
        p.setPen(QColor(110, 62, 24))
        p.drawText(QRectF(bx, by - 2, bw, bh), Qt.AlignCenter, self.text)
        p.restore()


# ---------------------------------------------------------------- 粒子
class Particles:
    def __init__(self):
        self.items = []

    def spawn(self, kind, x, y, count=1):
        for _ in range(count):
            vx = random.uniform(-45, 45)
            vy = random.uniform(-80, -20)
            life = random.uniform(0.8, 1.7)
            self.items.append({
                "kind": kind, "x": x, "y": y, "vx": vx, "vy": vy,
                "age": 0.0, "life": life, "size": random.uniform(8, 14),
                "rot": random.uniform(-30, 30),
            })

    def update(self, dt):
        for it in self.items:
            it["age"] += dt
            if it["kind"] in ("heart", "sparkle", "note", "zzz"):
                it["vy"] -= 12.0 * dt
            else:
                it["vy"] += 240.0 * dt
            it["x"] += it["vx"] * dt
            it["y"] += it["vy"] * dt
            it["rot"] += 40.0 * dt
        self.items = [i for i in self.items if i["age"] < i["life"]]

    def draw(self, p: QPainter):
        for it in self.items:
            alpha = 1.0 - it["age"] / it["life"]
            p.save()
            p.translate(it["x"], it["y"])
            p.rotate(it["rot"])
            p.setOpacity(clamp(alpha))
            p.setPen(Qt.NoPen)
            if it["kind"] == "heart":
                p.setBrush(QColor(255, 100, 120, int(230 * alpha)))
                p.drawEllipse(QPointF(-4, -3), 5, 5)
                p.drawEllipse(QPointF(4, -3), 5, 5)
                tri = QPolygonF([QPointF(-8, -1), QPointF(8, -1), QPointF(0, 9)])
                p.drawPolygon(tri)
            elif it["kind"] == "sparkle":
                p.setBrush(QColor(255, 224, 120, int(230 * alpha)))
                star = QPainterPath()
                for i in range(8):
                    ang = i * math.pi / 4
                    rr = 7 if i % 2 == 0 else 2.8
                    px, py = rr * math.cos(ang), rr * math.sin(ang)
                    if i == 0:
                        star.moveTo(px, py)
                    else:
                        star.lineTo(px, py)
                star.closeSubpath()
                p.drawPath(star)
            elif it["kind"] == "note":
                p.setPen(QPen(QColor(120, 90, 200, int(230 * alpha)), 4))
                p.setFont(QFont("PingFang SC", 16))
                p.drawText(QPointF(-8, 6), "♪")
            elif it["kind"] == "zzz":
                p.setPen(QPen(QColor(140, 130, 190, int(220 * alpha)), 4))
                p.setFont(QFont("PingFang SC", 14))
                p.drawText(QPointF(-6, 5), "z")
            else:
                p.setBrush(QColor(210, 190, 160, int(170 * alpha)))
                p.drawEllipse(QPointF(0, 0), it["size"] * 0.5, it["size"] * 0.5)
            p.restore()

# ---------------------------------------------------------------- 主窗口
class PetWindow(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
            | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        # 关键：App 失活时工具窗口也不隐藏（否则会被切到别的 App 时带走）
        self.setAttribute(Qt.WA_MacAlwaysShowToolWindow, True)
        self.setFixedSize(W, H)
        self.setMouseTracking(True)

        self.character = Character()
        self.bubble = SpeechBubble()
        self.particles = Particles()
        self.needs = {"mood": 0.75, "energy": 0.85, "hunger": 0.9, "social": 0.7}
        self.load_state()

        self.pressed = False
        self.drag_offset = QPoint()
        self.press_pos = QPoint()
        self.press_time = 0.0
        self.dragging = False
        self.drag_started = False
        self.last_cursor = QCursor.pos()
        self.mouse_inside = False
        self.mouse_local = QPointF(CX, 0)
        self.auto_timer = random.uniform(4.0, 7.0)
        self.attention_timer = random.uniform(45.0, 80.0)
        self.native_topmost_timer = 0.0

        self.anim = QPropertyAnimation(self, b"pos", self)
        self.anim.finished.connect(self._on_move_finished)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.setInterval(int(1000 / FPS))
        self.timer.start()

        self.setup_tray()
        self.move_to_floor(animate=False)
        self.bubble.show(say("start"), 4.0)

    # ---------- 状态 ----------
    def load_state(self):
        try:
            with open(SAVE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            for k in self.needs:
                self.needs[k] = clamp(data.get(k, self.needs[k]))
            pos = data.get("pos")
            if isinstance(pos, list) and len(pos) == 2:
                self.move(pos[0], pos[1])
        except Exception:
            pass

    def save_state(self):
        try:
            data = dict(self.needs)
            data["pos"] = [self.x(), self.y()]
            with open(SAVE_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
        except Exception:
            pass

    # ---------- 系统托盘 ----------
    def setup_tray(self):
        # 托盘图标直接复用完整角色的矢量渲染，保证和桌宠长得一样
        pix = QPixmap(80, 96)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)
        p.setWindow(56, 90, 248, 300)
        p.setViewport(0, 0, 80, 96)
        self.character.draw(p)
        p.end()
        self.tray = QSystemTrayIcon(QIcon(pix), self)
        self.tray.setToolTip(APP_NAME + " — 右键喂我、陪我玩")
        menu = QMenu()
        act_feed = QAction("喂小饼干", self)
        act_ball = QAction("扔皮球", self)
        act_dance = QAction("跳支舞", self)
        act_sleep = QAction("睡觉 / 叫醒", self)
        act_quit = QAction("退出", self)
        act_feed.triggered.connect(self.feed)
        act_ball.triggered.connect(self.play_ball)
        act_dance.triggered.connect(self.dance)
        act_sleep.triggered.connect(self.toggle_sleep)
        act_quit.triggered.connect(self.quit)
        for a in (act_feed, act_ball, act_dance, act_sleep):
            menu.addAction(a)
        menu.addSeparator()
        menu.addAction(act_quit)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray)
        self.tray.show()

    def _on_tray(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.character.mode == "sleep":
                self.wake()
            else:
                self.bubble.show(say("wave"), 2.4)

    # ---------- 主循环 ----------
    def tick(self):
        dt = 1.0 / FPS
        self.character.update(dt, self.mouse_local, self.mouse_inside)
        self.bubble.update(dt)
        self.particles.update(dt)

        cursor = QCursor.pos()
        inside = self.rect().contains(self.mapFromGlobal(cursor))
        if inside:
            self.mouse_local = self.mapFromGlobal(cursor)
        if inside and not self.mouse_inside:
            self.character.hover_elapsed = 0.0
        self.mouse_inside = inside
        if inside and self.character.mode in ("idle", "wander"):
            self.character.hover_elapsed += dt
            if self.character.hover_elapsed > 2.4:
                self.character.hover_elapsed = 0.0
                self.enter_mode("wave", text=say("wave"))
                self.spawn(CX, BODY_CY - 80, "sparkle", 5)

        # 需求系统：饿、累、孤单都会影响心情
        self.needs["hunger"] = clamp(self.needs["hunger"] - dt / (24.0 * 60.0))
        if self.character.mode == "sleep":
            self.needs["energy"] = clamp(self.needs["energy"] + dt / (3.0 * 60.0))
        else:
            self.needs["energy"] = clamp(self.needs["energy"] - dt / (70.0 * 60.0))
        self.needs["social"] = clamp(self.needs["social"] - dt / (45.0 * 60.0))
        target_mood = clamp(
            0.28 + 0.30 * self.needs["hunger"] + 0.20 * self.needs["energy"]
            + 0.22 * self.needs["social"], 0.0, 1.0)
        self.needs["mood"] = lerp(self.needs["mood"], target_mood, dt * 0.06)

        if self.character.mode == "sleep":
            if self.needs["energy"] > 0.96 and self.character.mode_elapsed > 25.0:
                self.wake()
            if random.random() < dt * 0.25:
                self.spawn(CX + random.uniform(-20, 20), BODY_CY - 90, "zzz", 1)
        else:
            self.needs["energy"] = clamp(self.needs["energy"] + dt / (40.0 * 60.0))

        # 饿 / 孤单会主动开口
        self.attention_timer -= dt
        if self.needs["hunger"] < 0.25 and self.attention_timer <= 0.0:
            self.attention_timer = random.uniform(30.0, 55.0)
            if self.character.mode not in ("eat", "sleep", "held"):
                self.enter_mode("hungry", text=say("hungry"))
        elif self.needs["social"] < 0.25 and self.attention_timer <= 0.0:
            self.attention_timer = random.uniform(40.0, 70.0)
            if self.character.mode not in ("sleep", "held", "pet"):
                self.enter_mode("wave", text=say("lonely"))
                self.needs["social"] = clamp(self.needs["social"] + 0.06)

        # 自主行为：有限时长模式到期后自动流转，避免动作卡住
        c = self.character
        if c.mode in ("eat", "ball", "land") and c.mode_elapsed > c.mode_duration:
            self.enter_mode("idle", text=None)
            self.auto_timer = random.uniform(4.0, 8.0)
        elif c.mode not in ("wander", "held", "pet", "eat", "ball", "land", "sleep") \
                and c.mode_elapsed > c.mode_duration:
            self.auto_timer = min(self.auto_timer, 0.0)

        if c.mode not in ("wander", "held", "pet", "eat", "ball", "land", "sleep"):
            self.auto_timer -= dt
            if self.auto_timer <= 0.0:
                self.choose_autonomous_action()

        # 兜底：如果鼠标松开事件丢失，手动结束按住/拎起状态
        if self.pressed and not (QApplication.mouseButtons() & Qt.LeftButton):
            was_dragging = self.dragging
            self.pressed = False
            self.character.held = False
            self.dragging = False
            self.drag_started = False
            if was_dragging:
                self.drop_to_floor()
            elif self.character.mode == "pet":
                self.enter_mode("idle", text=None)
                self.auto_timer = random.uniform(4.0, 8.0)

        # 拎起来
        if self.pressed and self.dragging and not self.drag_started:
            self.drag_started = True
            self.enter_mode("held", text=say("drag"))
            self.spawn(CX, BODY_CY - 60, "sparkle", 3)

        # 长按 = 抚摸（顺便停下正在进行的走动）
        if self.pressed and not self.dragging:
            hold_time = self.character.t - self.press_time
            if hold_time > 0.65 and self.character.mode != "pet":
                self.anim.stop()
                self.enter_mode("pet", text=say("pet"))
            if self.character.mode == "pet" and random.random() < dt * 7.0:
                self.spawn(CX + random.uniform(-52, 52),
                           BODY_CY + random.uniform(-40, 20), "heart", 1)
                self.needs["social"] = clamp(self.needs["social"] + 0.012)
                self.needs["mood"] = clamp(self.needs["mood"] + 0.006)

        # 周期性地重新确认原生置顶状态
        self.native_topmost_timer -= dt
        if self.native_topmost_timer <= 0.0:
            self.native_topmost_timer = 4.0
            self._assert_always_on_top()

        self.update()

    # ---------- 自主行为选择 ----------
    def choose_autonomous_action(self):
        hour = datetime.now().hour
        r = random.random()
        if self.needs["hunger"] < 0.22:
            self.auto_timer = random.uniform(6.0, 10.0)
            return self.enter_mode("hungry", text=say("hungry"))
        if self.needs["energy"] < 0.12 or ((hour >= 23 or hour < 7) and r < 0.35):
            self.auto_timer = 60.0
            return self.enter_mode("sleep", text=say("sleep"))
        if self.needs["social"] < 0.22:
            self.auto_timer = random.uniform(10.0, 16.0)
            return self.enter_mode("wave", text=say("lonely"))
        if self.needs["mood"] > 0.78 and r < 0.18:
            self.auto_timer = random.uniform(10.0, 16.0)
            return self.enter_mode("dance", text=say("dance"))
        roll = random.random()
        if roll < 0.34:
            self.auto_timer = random.uniform(4.0, 8.0)
            return self.enter_mode("idle", text=say("idle") if random.random() < 0.55 else None)
        if roll < 0.60:
            self.auto_timer = random.uniform(3.0, 6.0)
            self.start_wander()
            return None
        if roll < 0.72:
            self.auto_timer = random.uniform(7.0, 11.0)
            return self.enter_mode("glance", text=say("glance"))
        if roll < 0.82:
            self.auto_timer = random.uniform(9.0, 14.0)
            return self.enter_mode("stretch", text=say("stretch"))
        if roll < 0.92:
            self.auto_timer = random.uniform(12.0, 18.0)
            return self.enter_mode("yawn", text=say("yawn"))
        self.auto_timer = random.uniform(14.0, 22.0)
        return self.enter_mode("daydream", text=say("daydream"))

    def enter_mode(self, mode, duration=None, text=None):
        self.character.enter_mode(mode, duration)
        if text:
            self.bubble.show(text, 3.2)
        return self.character.mode_duration

    def active_screen(self):
        return self.app.screenAt(QCursor.pos()) or self.app.primaryScreen()

    def start_wander(self):
        screen = self.active_screen().availableGeometry()
        left = screen.left() + 8
        right = screen.right() - W + 8
        target = int(random.uniform(min(left, right), max(left, right)))
        distance = abs(target - self.x())
        duration = max(1.2, distance / 95.0)
        self.character.facing = 1.0 if target > self.x() else -1.0
        self.enter_mode("wander", duration + 0.01,
                        text=say("wander") if random.random() < 0.55 else None)
        self.anim.stop()
        self.anim.setDuration(int(duration * 1000))
        self.anim.setStartValue(self.pos())
        self.anim.setEndValue(QPoint(target, self.floor_y()))
        self.anim.setEasingCurve(QEasingCurve.InOutSine)
        self.anim.start()

    def _on_move_finished(self):
        if self.character.mode == "wander":
            self.enter_mode("idle", text=None)
            self.auto_timer = random.uniform(5.0, 9.0)
            self.spawn(CX - self.character.facing * 40, BASELINE, "dust", 3)

    # ---------- 交互 ----------
    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.show_context_menu(event.globalPosition().toPoint())
            return
        if event.button() == Qt.LeftButton:
            self.pressed = True
            self.press_pos = event.position().toPoint()
            self.press_time = self.character.t
            self.drag_offset = event.globalPosition().toPoint() - self.pos()
            self.dragging = False
            self.drag_started = False
            self.character.held = True

    def mouseMoveEvent(self, event):
        if self.pressed and (event.buttons() & Qt.LeftButton):
            global_pos = event.globalPosition().toPoint()
            if not self.dragging:
                start_global = self.press_pos + self.pos()
                if (global_pos - start_global).manhattanLength() > 8:
                    self.dragging = True
            if self.dragging:
                self.anim.stop()
                self.move(global_pos - self.drag_offset)
        event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        was_dragging = self.dragging
        hold_time = self.character.t - self.press_time
        self.pressed = False
        self.character.held = False
        if was_dragging:
            self.drop_to_floor()
            self.needs["social"] = clamp(self.needs["social"] + 0.06)
        elif hold_time < 0.34:
            self.poke()
        else:
            self.bubble.show(say("pet"), 2.4)
            self.needs["mood"] = clamp(self.needs["mood"] + 0.10)
            self.needs["social"] = clamp(self.needs["social"] + 0.08)
            if self.character.mode == "pet":
                self.enter_mode("idle", text=None)
                self.auto_timer = random.uniform(4.0, 8.0)
        self.dragging = False
        self.drag_started = False

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dance(highfive=True)

    def wheelEvent(self, event):
        if abs(event.angleDelta().y()) > 0:
            self.bubble.show(say("tickle"), 2.2)
            self.spawn(CX, BODY_CY - 40, "heart", 5)
            self.needs["mood"] = clamp(self.needs["mood"] + 0.06)
            self.enter_mode("wave", text=None)

    def leaveEvent(self, event):
        self.mouse_inside = False

    def poke(self):
        self.anim.stop()
        self.bubble.show(say("poke"), 2.4)
        n = random.choice([3, 4, 5])
        self.spawn(CX, BODY_CY - 40, random.choice(["heart", "sparkle"]), n)
        self.needs["mood"] = clamp(self.needs["mood"] + 0.05)
        self.needs["social"] = clamp(self.needs["social"] + 0.04)
        self.character.squash_x = 1.12
        self.character.squash_y = 0.88
        if random.random() < 0.4:
            self.character.facing *= -1
        self.enter_mode("idle", text=None)

    def feed(self):
        self.anim.stop()
        self.wake()
        self.enter_mode("eat", text=say("eat"))
        self.needs["hunger"] = 1.0
        self.needs["mood"] = clamp(self.needs["mood"] + 0.14)
        self.needs["social"] = clamp(self.needs["social"] + 0.06)
        self.character.cookie = {"x": -70.0, "y": 10.0, "r": 17.0}
        self.character.eat_t = 0.0

    def play_ball(self):
        self.anim.stop()
        self.wake()
        self.enter_mode("ball", text=say("ball"))
        self.character.spawn_ball()
        self.needs["mood"] = clamp(self.needs["mood"] + 0.12)
        self.needs["social"] = clamp(self.needs["social"] + 0.10)

    def dance(self, highfive=False):
        self.anim.stop()
        self.wake()
        self.enter_mode("dance", text=say("highfive" if highfive else "dance"))
        self.spawn(CX, BODY_CY - 100, "note", 3)
        self.needs["mood"] = clamp(self.needs["mood"] + 0.16)
        self.needs["social"] = clamp(self.needs["social"] + 0.10)

    def toggle_sleep(self):
        if self.character.mode == "sleep":
            self.wake()
        else:
            self.anim.stop()
            self.enter_mode("sleep", text=say("sleep"))

    def wake(self):
        was_sleeping = self.character.mode == "sleep"
        self.enter_mode("idle", text=say("wake") if was_sleeping else None)
        self.auto_timer = random.uniform(4.0, 8.0)

    def show_context_menu(self, global_pos):
        menu = QMenu(self)
        # 右键菜单也不要把 App 切到前台
        menu.setAttribute(Qt.WA_ShowWithoutActivating, True)
        menu.setWindowFlag(Qt.WindowDoesNotAcceptFocus, True)
        act_feed = menu.addAction("喂小饼干")
        act_ball = menu.addAction("扔皮球")
        act_dance = menu.addAction("跳支舞")
        act_sleep = menu.addAction("叫醒我" if self.character.mode == "sleep" else "睡觉")
        menu.addSeparator()
        act_quit = menu.addAction("退出")
        chosen = menu.exec(global_pos)
        if chosen == act_feed:
            self.feed()
        elif chosen == act_ball:
            self.play_ball()
        elif chosen == act_dance:
            self.dance()
        elif chosen == act_sleep:
            self.toggle_sleep()
        elif chosen == act_quit:
            self.quit()

    # ---------- 位置与粒子 ----------
    def floor_y(self):
        screen = self.active_screen().availableGeometry()
        return screen.bottom() - int(BASELINE) - 8

    def move_to_floor(self, animate=True):
        screen = self.active_screen().availableGeometry()
        left = screen.left() + 8
        right = max(left, screen.right() - W + 8)
        if self.x() < left or self.x() > right:
            self.move(random.randint(left, right), self.floor_y())
        elif animate:
            self.drop_to_floor()
        else:
            self.move(self.x(), self.floor_y())

    def drop_to_floor(self):
        screen = self.active_screen().availableGeometry()
        left = screen.left() + 8
        right = max(left, screen.right() - W + 8)
        x = int(clamp(self.x(), left, right))
        target = QPoint(x, self.floor_y())
        self.enter_mode("land", text=say("drop"))
        self.character.land_t = 0.0
        self.anim.stop()
        self.anim.setDuration(620)
        self.anim.setStartValue(self.pos())
        self.anim.setEndValue(target)
        self.anim.setEasingCurve(QEasingCurve.OutBounce)
        self.anim.start()
        QTimer.singleShot(180, lambda: self.spawn(CX - 20, BASELINE, "dust", 3))

    def spawn(self, x, y, kind, count=1):
        self.particles.spawn(kind, x, y, count)

    # ---------- 永远置顶 ----------
    def showEvent(self, event):
        super().showEvent(event)
        self._assert_always_on_top()

    def _assert_always_on_top(self):
        """保持置顶，但绝不抢焦点、绝不把 App 切到前台。

        原则：
        1. 只设置窗口 level / style / collectionBehavior；
        2. 窗口已经可见时绝不反复 raise 或 orderFront；
        3. 只有发现窗口真的不可见时才 orderFrontRegardless 一次。
        """
        flags = self.windowFlags()
        needed = (Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
                  | Qt.Tool | Qt.WindowDoesNotAcceptFocus)
        if (flags & needed) != needed:
            self.setWindowFlags(flags | needed)
            self.show()
        self.setAttribute(Qt.WA_MacAlwaysShowToolWindow, True)

        if _HAVE_APPKIT and self.app.platformName() != "offscreen":
            try:
                win_id = int(self.winId())
                if not win_id:
                    return
                view = _objc.objc_object(c_void_p=ctypes.c_void_p(win_id))
                ns_win = view.window()
                if ns_win is None:
                    return

                # 置顶层级：只在不是置顶层时设置
                if int(ns_win.level()) != int(NSFloatingWindowLevel):
                    ns_win.setLevel_(NSFloatingWindowLevel)

                # App 失活时也不隐藏
                ns_win.setHidesOnDeactivate_(False)

                # 非激活面板：点它、拖它都不会把 Python/Momo 切到前台
                style = int(ns_win.styleMask())
                if not (style & int(NSWindowStyleMaskNonactivatingPanel)):
                    ns_win.setStyleMask_(style | int(NSWindowStyleMaskNonactivatingPanel))

                # 跨 Space、覆盖全屏 App
                behavior = (NSWindowCollectionBehaviorCanJoinAllSpaces |
                            NSWindowCollectionBehaviorFullScreenAuxiliary)
                if int(ns_win.collectionBehavior()) != int(behavior):
                    ns_win.setCollectionBehavior_(behavior)

                # 只有真的看不见时才把它叫回来；平时不碰窗口顺序
                if not ns_win.isVisible():
                    ns_win.orderFrontRegardless()
            except Exception:
                pass

    # ---------- 绘制 ----------
    def paintEvent(self, event):
        p = QPainter(self)
        # 透明窗口必须用 Source 模式清屏，否则会留下残影
        p.setCompositionMode(QPainter.CompositionMode_Source)
        p.fillRect(self.rect(), Qt.transparent)
        p.setCompositionMode(QPainter.CompositionMode_SourceOver)
        self.character.draw(p)
        self.bubble.draw(p)
        self.particles.draw(p)
        p.end()

    def quit(self):
        self.save_state()
        self.tray.hide()
        self.app.quit()


# ---------------------------------------------------------------- 入口
def _become_menu_bar_style_app():
    """把 App 设为 Accessory 策略：不占 Dock、不抢前台、不打断用户。"""
    if not _HAVE_APPKIT:
        return
    try:
        from AppKit import NSApplication
        NSApplication.sharedApplication().setActivationPolicy_(
            NSApplicationActivationPolicyAccessory)
    except Exception:
        pass


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setQuitOnLastWindowClosed(False)
    _become_menu_bar_style_app()
    win = PetWindow(app)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
