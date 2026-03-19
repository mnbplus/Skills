/**
 * click_answers.js v2 - 按题号+字母精确填写
 * 核心改进：在每道题内部查找 [role=radio]，
 * 按顺序映射 A/B/C/D，不依赖全局索引，彻底消除偏移错误。
 *
 * 使用方式：
 * 1. 将下方 ANSWERS 替换为实际答案
 * 2. 复制整个函数体到 --fn 参数中运行
 *
 * pnpm openclaw browser evaluate --browser-profile winchrome --fn 'el => {
 *   const ANSWERS = {1:"C",2:"C",3:"B",...};
 *   // ... 粘贴 MAIN LOGIC 部分
 * }'
 */

// ============ ANSWERS - 修改这里 ============
const ANSWERS = {
  // 题号: 选项字母
  // 1: 'C',
  // 2: 'C',
  // ...
};
// ============================================

// MAIN LOGIC (复制到 evaluate --fn 时从这里开始)
el => {
  const ANSWERS = {}; // 替换为实际答案

  const questions = document.querySelectorAll('.questionLi');
  const results = [];
  const errors = [];

  questions.forEach((q, qi) => {
    const qNum = qi + 1;
    const answer = ANSWERS[qNum];

    if (!answer) {
      errors.push(`⚠️  题${qNum}: 未提供答案，跳过`);
      return;
    }

    // 在题目内部查找选项，不用全局索引
    const optionEls = Array.from(q.querySelectorAll('[role=radio]'));
    if (optionEls.length === 0) {
      errors.push(`❌ 题${qNum}: 未找到 [role=radio] 元素`);
      return;
    }

    // 构建字母→元素映射
    const labelMap = {};
    optionEls.forEach((opt, oi) => {
      const label = ['A','B','C','D','E'][oi];
      if (label) labelMap[label] = opt;
    });

    const targetOpt = labelMap[answer.toUpperCase()];
    if (!targetOpt) {
      errors.push(`❌ 题${qNum}: 选项${answer}不存在，可用: ${Object.keys(labelMap).join(',')}`);
      return;
    }

    // 检查是否已选中（避免重复点击）
    const alreadySelected = targetOpt.classList.contains('check') ||
      targetOpt.classList.contains('active') ||
      targetOpt.classList.contains('checked');

    if (alreadySelected) {
      results.push(`✅ 题${qNum}: 已选${answer}（跳过重复点击）`);
      return;
    }

    targetOpt.click();
    const preview = targetOpt.innerText.trim().replace(/\n/g,' ').substring(0, 25);
    results.push(`✅ 题${qNum}: 选${answer} → ${preview}`);
  });

  const summary = `填写完成 ${results.length}/${questions.length} 题`;
  return [summary, ...results, ...errors].join('\n');
}
