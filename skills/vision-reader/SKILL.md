---
name: vision-reader
description: 使用 qwen3-vision 分析图片。当用户发送图片（消息中包含 [media attached] 或 [Image from local path]）时使用。支持 OCR 文字提取、界面截图分析、错误截图诊断、代码识别。
metadata: {"openclaw":{"emoji":"👁️"}}
---

# Vision Reader — 图片理解

## 触发条件

消息中出现以下情况时自动调用：
- `[media attached: [image]]`
- `[Image from local path could not be read: ...]`（路径在错误信息里）
- 用户发了图片但辉夜看不到内容

## 核心命令

```bash
# 分析指定路径图片
python3 ~/.openclaw/workspace/scripts/vision.py <路径> [问题]

# 分析最新 QQ 图片
python3 ~/.openclaw/workspace/scripts/vision.py --latest

# OCR 提取文字
python3 ~/.openclaw/workspace/scripts/vision.py --ocr <路径>

# 分析网络图片
python3 ~/.openclaw/workspace/scripts/vision.py --url <URL>

# 预设模式
python3 ~/.openclaw/workspace/scripts/vision.py --preset error <路径>  # 错误截图
python3 ~/.openclaw/workspace/scripts/vision.py --preset ui <路径>     # 界面分析
python3 ~/.openclaw/workspace/scripts/vision.py --preset code <路径>   # 代码识别
python3 ~/.openclaw/workspace/scripts/vision.py --preset ocr <路径>    # 文字提取
```

## 图片路径获取规则

消息中的路径信息（按优先级）：
1. `[Image from local path could not be read: <路径>]` → 直接用该路径
2. `[media attached: [image]]` → 用 `--latest` 找最新图片
3. 用户描述的路径 → 直接用

QQ 图片默认保存在：`~/.openclaw/qqbot/downloads/`

## 工作流

1. 从消息中提取图片路径
2. 根据用户问题选择合适的模式（默认/OCR/preset）
3. 调用 vision.py 分析
4. 将结果回复给用户

## 注意

- OpenClaw 内置 `image` 工具对 hajimi provider 不可用
- vision.py 直接调用 hajimi qwen3-vision API，绕过 OpenClaw image 工具
- 脚本位置：`~/.openclaw/workspace/scripts/vision.py`
