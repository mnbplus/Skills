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

def run_ps(script, action, **kwargs):
    """运行 PowerShell 脚本"""
    ps_script = os.path.join(SCRIPT_DIR, script)

    ps_candidates = [
        'powershell',
        'powershell.exe',
        'pwsh',
        'pwsh.exe',
        '/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe',
        '/mnt/c/Program Files/PowerShell/7/pwsh.exe',
    ]

    last_error = None
    for ps_bin in ps_candidates:
        cmd = [ps_bin, '-ExecutionPolicy', 'Bypass', '-File', ps_script, '-Action', action]
        for k, v in kwargs.items():
            if v is not None:
                cmd += [f'-{k}', str(v)]
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=30)

            def _decode(data):
                if not data:
                    return ''
                for enc in ('utf-8', 'gbk', 'gb18030', 'utf-16le'):
                    try:
                        return data.decode(enc)
                    except Exception:
                        pass
                return data.decode('utf-8', errors='replace')

            stdout = _decode(result.stdout)
            stderr = _decode(result.stderr)
            print(stdout)
            if stderr:
                print(stderr, file=sys.stderr)
            return
        except FileNotFoundError as e:
            last_error = e
            continue
        except subprocess.TimeoutExpired:
            print(json.dumps({'success': False, 'error': '命令超时'}))
            return

    print(json.dumps({'success': False, 'error': 'PowerShell 未找到，请在 Windows 环境运行'}))

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
