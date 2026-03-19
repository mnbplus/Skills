---
name: wsl-winbridge
description: "🖥️ Windows 桌面全控 — 专为 WSL + Windows 混合环境设计。Python 引擎负责截图/鼠标键盘，PowerShell 引擎负责窗口管理/VSCode/进程，统一 ctrl.py 入口自动路由。WSL 用户直接调用 PowerShell 脚本无需额外配置。无需 API Key。"
metadata: {"openclaw":{"emoji":"🖥️"}}
---

# 🪟 WSL WinBridge — WSL→Windows 桥接桌面控制

> 专为 **WSL + Windows 混合环境**设计的桌面控制技能。
> 在 WSL 里直接控制 Windows 桌面——无需切换环境，一个命令搞定。

## ✨ 核心特点

- **WSL 原生支持** — PowerShell 引擎在 WSL 下直接控制 Windows 桌面，无需额外配置
- **双引擎架构** — Python(mss/pyautogui) 负责截图/输入，PowerShell(Win32 API) 负责窗口管理
- **统一入口** — `ctrl.py` 自动选择引擎，AI 只需记一个命令
- **优雅降级** — Python GUI 库缺失时自动提示安装，不崩溃
- **无需 API Key** — 完全本地运行，无网络依赖

## 🚀 快速开始

```bash
# 安装后（clawhub install win-desktop）
CTRL="python3 ~/.openclaw/skills/win-desktop/scripts/ctrl.py"

# 截图
$CTRL screenshot

# 鼠标/键盘
$CTRL click 960 540        # 点击屏幕坐标
$CTRL type '你好世界'       # 输入文字（支持中文）
$CTRL hotkey ctrl s        # 组合键

# 窗口管理（WSL 下也可用）
$CTRL windows              # 列出所有窗口
$CTRL focus Chrome         # 聚焦 Chrome
$CTRL snap Chrome left     # 贴靠左半屏
$CTRL launch notepad.exe   # 启动记事本

# 系统信息
$CTRL displays             # 显示器信息
$CTRL active-window        # 当前活跃窗口
$CTRL processes            # 进程列表
$CTRL info                 # 系统信息
```

## 🏗️ 架构说明

```
ctrl.py（统一入口）
├── Python 引擎 (desktop_ctrl.py)
│   ├── 截图 (mss + Pillow)
│   ├── 鼠标控制 (pyautogui)
│   ├── 键盘输入 (pyautogui)
│   └── 剪贴板 (win32clipboard)
└── PowerShell 引擎
    ├── app-control.ps1    — 窗口管理（列出/聚焦/移动/贴靠）
    ├── input-sim.ps1      — 输入模拟（精细控制）
    ├── screen-info.ps1    — 屏幕信息 + PowerShell 截图
    ├── process-manager.ps1— 进程管理
    └── vscode-control.ps1 — VSCode 专项控制
```

## 🪟 WSL 用户说明

WSL 下 Python GUI 库（mss/pyautogui）无法直接控制 Windows 桌面，但 **PowerShell 引擎完全可用**：

| 功能 | WSL 可用？ | 说明 |
|------|-----------|------|
| 窗口列出/聚焦/移动 | ✅ | PowerShell Win32 API |
| 窗口贴靠/最大化 | ✅ | PowerShell |
| 进程管理 | ✅ | PowerShell |
| VSCode 控制 | ✅ | PowerShell |
| 截图 | ✅ | PowerShell screen-info.ps1 |
| 鼠标点击 | ⚠️ | 需 Windows 原生 Python |
| 键盘输入 | ⚠️ | 需 Windows 原生 Python |

## 📦 依赖

**PowerShell 引擎**（WSL/Windows 均可）：无需安装，Windows 内置。

**Python 引擎**（Windows 原生 Python）：
```bash
pip install mss pyautogui Pillow pywin32
```

## 🔒 安全设计

- `execute_command` 方法已禁用，不执行任意系统命令
- 进程白名单限制，不能随意 kill 系统进程
- 关闭窗口/结束进程前建议用户确认
