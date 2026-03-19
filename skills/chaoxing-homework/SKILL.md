---
name: chaoxing-homework
description: 自动完成超星学习通作业。支持单选题、多选题、判断题。使用浏览器自动化读取题目（含LaTeX公式精确提取）、AI解答、自动填写并提交。当用户提到「学习通作业」「chaoxing」「超星」「帮我做作业」时使用。
---

# Chaoxing Homework Skill v2

自动完成超星学习通（mooc1/mooc2）作业的完整流程。每次完成后记录错题，持续提升精度。

## 前置条件

- `winchrome` 浏览器 profile 已登录学习通
- OpenClaw browser 工具可用
- 启动前先读取 `references/mistakes-log.md` 了解历史错题规律

---

## Step 1: 定位并进入作业

```bash
cd /home/maniubi/openclaw

# 导航到学习通首页
pnpm openclaw browser navigate --browser-profile winchrome 'https://i.chaoxing.com' 2>&1

# 快照找课程（关键词：课程名）
pnpm openclaw browser snapshot --browser-profile winchrome 2>&1 | grep -A5 '课程名关键词'

# 找到课程后，用 evaluate 获取作业直链（避免 goTask click 失效问题）
pnpm openclaw browser evaluate --browser-profile winchrome \
  --fn 'el => { const items = document.querySelectorAll("li[data]"); return JSON.stringify(Array.from(items).map(li=>({text:li.innerText.substring(0,40), url:li.getAttribute("data")}))); }' 2>&1 | grep -v plugins

# 直接导航到作业 URL
pnpm openclaw browser navigate --browser-profile winchrome '<作业URL>' 2>&1
```

---

## Step 2: 提取题目（精确版）

**⚠️ 核心原则：永远在选项元素内部查 img[data]，不用全局图片索引！**

```bash
# 运行精确提取脚本（在选项元素内部查 LaTeX，消除偏移错误）
pnpm openclaw browser evaluate --browser-profile winchrome \
  --fn "$(tr '\n' ' ' < ~/.openclaw/skills/chaoxing-homework/scripts/extract_questions.js)" \
  2>&1 | grep -v plugins > /tmp/questions.json

cat /tmp/questions.json
```

输出格式：每道题包含 `stemText`、`stemLatex`（题干公式）、`options`（含各选项的 `label`/`text`/`latex`）。

---

## Step 3: AI 解答

根据提取结果逐题分析，输出答案映射 `{题号: 字母}`。

### 解题策略速查

**函数相同判断**
- 定义域 + 对应法则都相同才算相同函数
- f(x)=(x²-1)/(x+1) vs g(x)=x-1 → 不同（f在x=-1无定义）
- f(x)=ln(x²) vs g(x)=2ln|x| → 相同（定义域均为x≠0）

**定义域**
- √u → u≥0；ln(u) → u>0；1/u → u≠0
- 复合函数：各层条件取交集

**极限/无穷小判断**
- x→∞时 1/x·arctan(x)→0 → 无穷小
- x→∞时 x·sin(1/x)→1 → 常量极限

**导数与单调性**
- f'(x)>0 → 单调增；f'(x)<0 → 单调减
- 命题：不连续→不可导（✓）；不可导→不连续（✗，如|x|在0点）

**积分代码题（sympy）**
- `integrate(expr, (x, a, b))` → 定积分
- `integrate(expr, x)` → 不定积分
- 含 |cos(x)| 或分段函数 → 需分段积分，不能直接用单一 integrate
- ⚠️ 历史错题：√(sin³x-sin⁵x) 含|cos(x)|，正确写法是分段处理

**sympy 代码填空**
- 使用符号变量前必须先 `x = symbols('x')`
- `diff(y, x, n)` → y对x的n阶导数
- `y.subs(x, val)` → 代入数值

---

## Step 4: 填写答案（按题内部映射，消除偏移）

```bash
# 将 ANSWERS 替换为实际答案后运行
pnpm openclaw browser evaluate --browser-profile winchrome --fn 'el => {
  const ANSWERS = {1:"C",2:"C",3:"B",4:"B",5:"C",6:"B",7:"C",8:"B",9:"C",10:"D",11:"A",12:"C"};
  const questions = document.querySelectorAll(".questionLi");
  const results = [], errors = [];
  questions.forEach((q, qi) => {
    const qNum = qi + 1;
    const answer = ANSWERS[qNum];
    if (!answer) { errors.push("⚠️ 题"+qNum+": 未提供答案"); return; }
    const optionEls = Array.from(q.querySelectorAll("[role=radio]"));
    if (!optionEls.length) { errors.push("❌ 题"+qNum+": 无选项"); return; }
    const labelMap = {};
    optionEls.forEach((opt, oi) => { labelMap[["A","B","C","D","E"][oi]] = opt; });
    const target = labelMap[answer.toUpperCase()];
    if (!target) { errors.push("❌ 题"+qNum+": 选项"+answer+"不存在"); return; }
    target.click();
    results.push("✅ 题"+qNum+": 选"+answer+" → "+target.innerText.trim().replace(/\n/g," ").substring(0,20));
  });
  return ["填写 "+results.length+"/"+questions.length+" 题", ...results, ...errors].join("\n");
}' 2>&1 | grep -v plugins
```

---

## Step 5: 提交前验证

```bash
# 运行验证脚本，确认所有题目已选择
pnpm openclaw browser evaluate --browser-profile winchrome \
  --fn "$(tr '\n' ' ' < ~/.openclaw/skills/chaoxing-homework/scripts/verify_answers.js)" \
  2>&1 | grep -v plugins
```

若输出 `🟢 全部 N 题已作答` 才继续提交。否则补填未作答题目。

---

## Step 6: 提交

```bash
# 获取最新快照找提交按钮 ref
pnpm openclaw browser snapshot --browser-profile winchrome 2>&1 | grep -i '提交'

# 点击提交
pnpm openclaw browser click --browser-profile winchrome <提交ref> 2>&1

# 等待确认弹窗
sleep 2 && pnpm openclaw browser snapshot --browser-profile winchrome 2>&1 | grep -i '确定\|确认'

# 点击确定
pnpm openclaw browser click --browser-profile winchrome <确定ref> 2>&1
```

---

## Step 7: 结果分析 & 错题记录

```bash
# 提交后运行验证脚本（自动切换为结果模式）
sleep 3 && pnpm openclaw browser evaluate --browser-profile winchrome \
  --fn "$(tr '\n' ' ' < ~/.openclaw/skills/chaoxing-homework/scripts/verify_answers.js)" \
  2>&1 | grep -v plugins
```

将错题追加到 `references/mistakes-log.md`，格式：
```
## YYYY-MM-DD 课程名 · 作业名 (得分/满分)
### 题N ❌ (我选X，正确Y)
- 题干：...
- 分析：...
- 根因：...
- 修复：...
```

向用户汇报：得分、错题列表、根因简述。

---

## 已知问题速查

| 问题 | 解决方案 |
|------|----------|
| 图片防盗链，curl 下载空文件 | 用 img[data] LaTeX 提取，不下载图片 |
| 全局图片索引偏移（最常见错误） | 在每道题/选项元素内部单独查 img[data] |
| screenshot/click ref 超时 | 用 evaluate 直接操作 DOM |
| goTask(this) 点击无效 | 读 li[data]
## ⚠️ 关键修复（v2.1）

### 必须用 addChoice() 而非 .click()

学习通选项的 onclick 是 `addChoice(this)`，直接 `.click()` 不会写入 hidden input，答案不会被提交！

正确填写方式：
```js
// ❌ 错误
targetOpt.click();

// ✅ 正确
addChoice(targetOpt);
```

验证方法：检查 `input[id*=answer]` 的 value 是否有字母值（A/B/C/D）。

### 大于 vs 大于等于

- 含泰勒展开余项的不等式：注意 x=0（或其他边界点）时是否等号成立
- sinx ≥ x-x³/6（x≥0 时），x=0 时取等 → 选「大于等于」
- 一般题干说「当 x>0 时」才是严格大于

### 题干图片无 LaTeX 时的处理

部分题干图片没有 `data` 属性（服务器直接返回图片，非 edrawmath 渲染），此时：
1. 根据选项反推题干（如选项都是数值，猜测是极限题）
2. 参考 `mistakes-log.md` 中同类题的历史答案
3. 如果实在无法判断，向用户报告哪些题无法自动识别

常见无 LaTeX 极限题对照：
- 选项含 1/2, 1/3, 1/4, 1/5 → 可能是：
  - lim(x→0)(x-arctan x)/x³ = 1/3
  - lim(x→0)(1-cos x)/x² = 1/2
  - lim(x→0)(e^x-1-x)/x² = 1/2

## ⚠️ 关键修复（v2.2）：截图题干图片

**必须在进入 dowork 页面后、填写答案前立即运行截图！**

```bash
# Step 2.5: 截取所有无LaTeX的题干图片（在 dowork 页面时立即执行）
mkdir -p /tmp/cx_stems
node ~/.openclaw/skills/chaoxing-homework/scripts/screenshot_stems.cjs /tmp/cx_stems

# 逐张分析
for f in /tmp/cx_stems/*.png; do
  echo "=== $f ==="
  python3 ~/.openclaw/workspace/scripts/vision.py "$f" '请识别图中数学公式或表达式，只输出公式本身'
done
```

**注意事项：**
- 截图脚本使用 CDP 直接截图，不经过 gateway（无超时问题）
- 必须在 dowork 页面打开时运行，提交后图片消失
- 截图后立即用 vision 分析，得到公式再解题
- 整个流程：进入dowork → 截图 → vision分析 → 解题 → 填写 → 验证 → 提交

## 🚀 v2.3 全自动流程（auto_solve.cjs）

**最简单的完整流程：**

```bash
SKILL=~/.openclaw/skills/chaoxing-homework/scripts
OUT=/tmp/cx_work

# Step 1: 进入作业 dowork 页面后立即运行
node $SKILL/auto_solve.cjs extract $OUT
# 输出: questions.json + 所有无LaTeX题干截图

# Step 2: 分析题干截图（如有）
for f in $OUT/q*_img*.png; do
  echo "=== $f ==="
  python3 ~/.openclaw/workspace/scripts/vision.py "$f" '识别图中数学公式'
done

# Step 3: 读取 questions.json，结合截图分析，用AI解题
cat $OUT/questions.json

# Step 4: 填写答案（将答案替换为实际结果）
node $SKILL/auto_solve.cjs submit $OUT '{"1":"A","2":"B","3":"C"}'

# Step 5: 快照找提交按钮，点击提交
pnpm openclaw browser snapshot --browser-profile winchrome 2>&1 | grep '提交'
pnpm openclaw browser click --browser-profile winchrome <ref> 2>&1
# 确认弹窗再点一次确定
```

**auto_solve.cjs 优势：**
- 截图 + 提取 + 填写三合一
- 使用 `addChoice()` 正确触发表单（已修复 click bug）
- 自动验证 hidden input 是否写入
- 不经过 gateway，无超时问题

## ⚠️ v2.4 OCR 工具链（多级降级）

图片识别优先级：

1. **qwen3-vision**（hajimi，最强，支持数学公式）
   ```bash
   python3 ~/.openclaw/workspace/scripts/vision.py <img> '识别数学公式'
   ```

2. **tesseract**（本地，免费，已安装，对清晰文字有效）
   ```bash
   tesseract <img> stdout --psm 6 2>/dev/null
   # 放大后再识别效果更好：
   convert <img> -resize 300% /tmp/big.png && tesseract /tmp/big.png stdout --psm 6
   ```

3. **CDP Page.getResourceContent**（获取原始图片文件，不依赖任何API）
   ```bash
   node ~/.openclaw/skills/chaoxing-homework/scripts/get_images.cjs <output_dir>
   ```

4. **人工识别**（发给 Master 直接看）

## 关键数学公式速查（泰勒展开）

| 极限 | 结果 | 推导 |
|------|------|------|
| lim(x→0)(sinx-xcosx)/sin³x | 1/3 | sinx-xcosx=x³/3, sin³x≈x³ |
| lim(x→0)(eˣ-1-x-x²/2)/(sinx-xcosx) | 1/2 | 分子≈x³/6, 分母≈x³/3 |
| lim(x→0)(x-arctan x)/x³ | 1/3 | arctan x=x-x³/3+... |
| lim(x→0)(1-cosx)/x² | 1/2 | cosx=1-x²/2+... |
| lim(x→0)(eˣ-1-x)/x² | 1/2 | eˣ=1+x+x²/2+... |
| lim(x→0)(sinx-x)/x³ | -1/6 | sinx=x-x³/6+... |
| lim(x→0)(tanx-x)/x³ | 1/3 | tanx=x+x³/3+... |
| lim(x→0)(x-sin x)/x³ | 1/6 | 同上取负 |

## 不等式边界注意事项
- sinx ≥ x-x³/6（x≥0），x=0时取等 → 选「大于等于」不是「大于」
- 含根号积分含|cos|或|sin| → 必须分段处理
