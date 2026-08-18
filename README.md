# Momo 桌宠 🍊

一个轻量、低打扰的 macOS 桌面宠物。Momo 会自己溜达、发呆、打盹、跳舞、要吃的，也会追着你的鼠标看。

当前 `ui/apple-polish` 版本保留原来的鸡蛋形象与 60 FPS 动画核心，同时加入更接近 macOS 原生习惯的菜单栏、状态卡、主题与偏好设置体验。

![Momo](docs/preview.png)

## 快速开始

双击 `start.command`。首次运行会自动创建虚拟环境并安装 PySide6 + pyobjc。

也可以在终端运行：

```bash
cd 本目录
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
./.venv/bin/python momo_app.py
```

## Apple UI 版本

- 半透明对话气泡，支持浅色 / 深色 / 跟随系统
- macOS 菜单栏使用单色鸡蛋 mask 图标，自动适配明暗菜单栏
- 菜单栏菜单尽量交给 macOS 原生样式，不强行套 Qt 皮肤
- 点击菜单栏图标打开状态 Popover，再次点击可收起，点击外部自动关闭
- 状态卡显示心情、饱食、精力和当前行为
- 喂食、玩耍、跳舞、睡觉快捷操作
- 显示 / 隐藏 Momo、召回到当前屏幕
- 心情 HUD 支持“互动时 / 始终 / 关闭”，默认低打扰的“互动时”
- 偏好设置：浅色 / 深色 / 跟随系统、透明度、气泡时长、气泡开关、HUD 模式
- 系统明暗模式变化时，跟随系统主题会自动刷新
- UI 配置会与需求状态一起保存到 `~/.momo_pet.json`

## 怎么和 Momo 玩

| 操作 | Momo 的反应 |
| --- | --- |
| 单击 | 被戳一下：惊讶、脸红、冒小心心 |
| 双击 | 击掌 + 即兴跳舞 |
| 按住不动 | 抚摸：舒服得冒爱心，心情和亲密度上升 |
| 按住拖动 | 把它拎起来；松手后弹跳落地 |
| 鼠标悬停 | 它会盯着光标看，看久了会挥手 |
| 滚轮 | 挠痒痒 |
| 右键 Momo | 打开完整快捷菜单 |
| 点击菜单栏图标 | 打开 / 收起 Momo 状态卡 |

## 自主行为

Momo 有四个需求：**饱腹、精力、亲密度、心情**，会随时间变化。

- 🍪 饿了会主动提醒你
- 😴 累了或深夜会自己睡觉
- 🥺 太久没人理会会主动求关注
- 😄 心情好会唱歌、跳舞、散步、发呆、伸懒腰
- 🚶 会沿屏幕底边自己溜达

## 文件说明

```text
pixar_pet.py                   角色动画、行为、需求系统与原生置顶逻辑
momo_app.py                    App、菜单栏、Popover、HUD、主题协调层
momo_ui.py                     状态卡、偏好设置、主题 token 与通用 UI 组件
requirements.txt               依赖
start.command                  macOS 双击启动入口
tools/render_actual_preview.py 通过 Qt widget.grab() 生成真实 UI 预览
make_preview.py                角色状态预览辅助脚本
docs/preview.png               角色预览图
```

## 常见问题

- **没有安装依赖**：双击 `start.command`，会自动安装。
- **桌宠不见了**：点击菜单栏 Momo 图标，或菜单里选择“召回到当前屏幕”。
- **不想它挡住画面**：菜单或状态卡里选择“隐藏 Momo”，再次点击菜单栏图标即可召回。
- **退出**：右键 Momo 或菜单栏菜单 → “退出 Momo”。
- **始终置顶**：Qt 置顶 + macOS `NSFloatingWindowLevel`，可跨 Space / 全屏显示。
- **不会抢焦点**：Momo 使用 NonactivatingPanel，App 运行在 Accessory 模式，不占 Dock、不进 Cmd-Tab。

## 技术说明

- PySide6 / QPainter 全矢量绘制
- 60 FPS 角色动画
- UI 与角色行为分层：`pixar_pet.py` 保持核心稳定，UI 由 `momo_app.py` + `momo_ui.py` 扩展
- Qt `WindowStaysOnTopHint` + macOS AppKit 原生窗口层级
- 系统字体与动态 Color Scheme 适配
- 状态与 UI 偏好持久化
- GitHub Actions 可生成当前代码的真实 Qt UI 截图，避免把概念图当运行态
