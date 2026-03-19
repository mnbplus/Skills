#!/usr/bin/env python3
"""
Win Desktop — 统一控制入口
自动定位脚本目录，分发到 Python 或 PowerShell 引擎

用法:
  python3 ctrl.py <command> [args...]

命令:
  screenshot           截图
  click <x> <y>        鼠标点击
  move <x> <y>         鼠标移动
  mouse                获取鼠标位置
  type <text>          输入文字
  press <key>          按键
  hotkey <k1> <k2>     组合键
  processes            进程列表
  clipboard get        读剪贴板
  clipboard set <text> 写剪贴板
  info                 系统信息
  windows              列出所有窗口 (PowerShell)
  launch <app>         启动程序 (PowerShell)
  focus <title>        聚焦窗口 (PowerShell)
  close <title>        关闭窗口 (PowerShell)
  snap <title> <pos>   贴靠窗口 left/right (PowerShell)
  displays             显示器信息 (PowerShell)
  active-window        当前活跃窗口 (PowerShell)
"""

import os
import sys
import json
import subprocess

# 脚本目录（自动定位）
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PY_CTRL = os.path.join(SCRIPT_DIR, 'desktop_ctrl.py')

# WSL 下 powershell.exe 可能不在 PATH，尝试多个路径
PS_PATHS = [
    'powershell.exe',
    '/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe',
    '/mnt/c/Windows/SysWOW64/WindowsPowerShell/v1.0/powershell.exe',
]

def find_powershell():
    import shutil
    for ps in PS_PATHS:
        if shutil.which(ps) or os.path.exists(ps):
            return ps
    return None

POWERSHELL = find_powershell()

# Windows 临时目录（用于存放 PS1 脚本）
WIN_TEMP = os.path.expanduser('~') + '/../..'
try:
    _wt = subprocess.run(['wslpath', '-u', 'C:\\Windows\\Temp'], capture_output=True, timeout=5)
    WIN_TEMP_LINUX = _wt.stdout.decode().strip()
except:
    WIN_TEMP_LINUX = '/mnt/c/Windows/Temp'


def run_ps(script, action, **kwargs):
    """运行 PowerShell 脚本（复制到 Windows Temp 再执行）"""
    ps_src = os.path.join(SCRIPT_DIR, script)
    ps_dst = os.path.join(WIN_TEMP_LINUX, script)
    if not POWERSHELL:
        print(json.dumps({'success': False, 'error': 'PowerShell 未找到'}))
        return
    # 如果 .ps1 不存在但 .ps1.txt 存在（clawhub 打包限制），自动转换
    import shutil
    if not os.path.exists(ps_src) and os.path.exists(ps_src + '.txt'):
        shutil.copy2(ps_src + '.txt', ps_src)
    # 复制 PS1 到 Windows 可访问的目录
    try:
        shutil.copy2(ps_src, ps_dst)
    except Exception as e:
        print(json.dumps({'success': False, 'error': f'复制脚本失败: {e}'}))
        return
    # 获取 Windows 路径
    try:
        wp = subprocess.run(['wslpath', '-w', ps_dst], capture_output=True, timeout=5)
        win_script = wp.stdout.decode().strip()
    except:
        win_script = f'C:\\Windows\\Temp\\{script}'
    # 构建参数
    params = f'-Action {action}'
    for k, v in kwargs.items():
        if v is not None and v != '':
            params += f' -{k} "{v}"'
    ps_cmd = f'& "{win_script}" {params}'
    cmd = [POWERSHELL, '-ExecutionPolicy', 'Bypass', '-NoProfile', '-Command', ps_cmd]
    for k, v in kwargs.items():
        if v is not None:
            cmd += [f'-{k}', str(v)]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=30)
        # PowerShell 在 Windows 下可能返回 GBK 编码
        for enc in ['utf-8', 'gbk', 'cp936', 'latin-1']:
            try:
                out = result.stdout.decode(enc)
                break
            except:
                continue
        else:
            out = result.stdout.decode('utf-8', errors='replace')
        print(out)
        if result.stderr:
            err = result.stderr.decode('utf-8', errors='replace')
            print(err, file=sys.stderr)
    except FileNotFoundError:
        print(json.dumps({'success': False, 'error': 'PowerShell 未找到，WSL 用户请确认 powershell.exe 在 PATH 中'}))
    except subprocess.TimeoutExpired:
        print(json.dumps({'success': False, 'error': '命令超时'}))

def run_py(*args):
    """运行 Python 控制脚本"""
    cmd = [sys.executable, PY_CTRL] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    cmd = sys.argv[1].lower()
    args = sys.argv[2:]

    # Python 引擎命令
    py_commands = {'screenshot', 'click', 'move', 'mouse', 'type', 'press',
                   'hotkey', 'processes', 'clipboard', 'info', 'kill'}

    # PowerShell 引擎命令
    ps_commands = {
        'windows': ('app-control.ps1', 'list-windows', {}),
        'launch': ('app-control.ps1', 'launch', {'Target': args[0] if args else ''}),
        'focus': ('app-control.ps1', 'focus', {'Target': args[0] if args else ''}),
        'close': ('app-control.ps1', 'close', {'Target': args[0] if args else ''}),
        'minimize': ('app-control.ps1', 'minimize', {'Target': args[0] if args else ''}),
        'maximize': ('app-control.ps1', 'maximize', {'Target': args[0] if args else ''}),
        'snap': ('app-control.ps1', 'snap', {'Target': args[0] if args else '', 'Position': args[1] if len(args) > 1 else 'left'}),
        'displays': ('screen-info.ps1', 'displays', {}),
        'active-window': ('screen-info.ps1', 'active-window', {}),
        'ps-screenshot': ('screen-info.ps1', 'screenshot', {'OutputPath': args[0] if args else ''}),
        'ps-clipboard-get': ('screen-info.ps1', 'clipboard-get', {}),
        'ps-clipboard-set': ('screen-info.ps1', 'clipboard-set', {'Text': args[0] if args else ''}),
    }

    if cmd in py_commands:
        run_py(cmd, *args)
    elif cmd in ps_commands:
        script, action, kwargs = ps_commands[cmd]
        run_ps(script, action, **kwargs)
    else:
        print(json.dumps({'success': False, 'error': f'未知命令: {cmd}，运行 ctrl.py 查看帮助'}))
        sys.exit(1)

if __name__ == '__main__':
    main()
