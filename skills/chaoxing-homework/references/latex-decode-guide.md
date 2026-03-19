# LaTeX 解码指南

学习通题目图片的 `data` 属性包含 URL 编码的 LaTeX，格式如下：

## 解码方式

```
URL decode → 去掉首尾引号 → 去掉 \\[ 和 \\] 包裹 → 得到 LaTeX
```

## 常见公式对照表

| LaTeX | 含义 |
|-------|------|
| `\\frac{a}{b}` | a/b 分数 |
| `\\sqrt{x}` | √x |
| `\\infty` | ∞ |
| `\\to` | → |
| `\\lim` | lim |
| `\\int` | ∫ |
| `\\sum` | Σ |
| `x\\mathop{}\\nolimits^{2}` | x² |
| `\\left( a, b \\right)` | 开区间 (a,b) |
| `\\left[ a, b \\right]` | 闭区间 [a,b] |
| `\\cup` | ∪ (并集) |
| `\\cap` | ∩ (交集) |
| `\\ln` | ln |
| `\\sin`, `\\cos`, `\\tan` | 三角函数 |
| `\\arctan` | arctan |
| `f \\left( x \\left) = ... \\right. \\right.` | f(x) = ... |
| `\\frac{d}{dx}` | 对x求导 |
| `\\mathop{lim}\\limits_{x \\to a}` | x→a 时的极限 |
| `\\int_a^b` | 从a到b的定积分 |

## 本次作业提取示例

```
img0: f(x)=(x²-1)/(x+1), g(x)=x-1      → 题1选项A
img1: f(x)=√(x²), g(x)=x               → 题1选项B  
img2: f(x)=ln(x²), g(x)=2ln|x|        → 题1选项C ✓相同函数
img3: f(x)=√((x-1)/(x+1)), g(x)=...   → 题1选项D
img4: y=1+√x                           → 题2题干
img5: (-1,+∞)                          → 题2选项A
img6: (-∞,0]                           → 题2选项B
img7: [0,+∞)                           → 题2选项C ✓正确答案
img8: (-∞,1]                           → 题2选项D
```

## 常见陷阱

1. **题干图片 vs 选项图片**: 题干图片通常宽度 > 150px，选项图片较小
2. **img 顺序**: 按 DOM 顺序，题干先于选项
3. **部分题无图片**: 如纯文字题，LaTeX 列表中无对应项
4. **多图题干**: 一道题可能有多个 LaTeX 图片（如条件+表达式分开）

## 图片与题目对应算法

```python
# 伪代码
img_index = 0
for q_index, question in enumerate(questions):
    stem_img_count = len(question.stem_imgs)
    option_img_counts = [len(opt.imgs) for opt in question.options]
    
    stem_latexes = latexes[img_index : img_index + stem_img_count]
    img_index += stem_img_count
    
    for opt, count in zip(question.options, option_img_counts):
        opt.latexes = latexes[img_index : img_index + count]
        img_index += count
```
